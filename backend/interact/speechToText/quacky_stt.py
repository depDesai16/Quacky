#!/usr/bin/env python3
"""
Quacky Speech-to-Text

Architecture:
- STT thread (producer) listens and enqueues commands
- AI worker thread (consumer) processes commands sequentially from a queue

Features:
- Idle timeout (15s): if ACTIVE and no commands for 15s -> deactivate and require wake word again
- Clean state machine: INACTIVE -> LISTENING -> THINKING -> RESPONDING
- Explicit active flag (no inference from timestamps)
- Graceful shutdown via stop flag + sentinel in queue (no os._exit)
- Terminal logs: what STT heard + state transitions

Update (non-breaking):
- Optional response_handler so RESPONDING can be set BEFORE printing/TTS.
  - If response_handler is set: worker sets RESPONDING then calls handler(result)
  - If not set: preserves existing behavior (logs AI response if result is a string)
"""
import os
import queue
import sys
import threading
import time
from enum import Enum, auto
from typing import Any, Callable, Optional

import pyaudio
import speech_recognition as sr

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)


class State(Enum):
    INACTIVE = auto()   
    LISTENING = auto()  
    THINKING = auto()     
    RESPONDING = auto()   
    SHUTTING_DOWN = auto()


class QuackySpeechToText:
    def __init__(
        self,
        mic_index=None,
        idle_timeout_seconds: int = 15,
        require_wake_word: bool = True,
    ):
        self.recognizer = sr.Recognizer()
        self.microphone: Optional[sr.Microphone] = None

        self.wake_word = "hey quacky"
        self.require_wake_word = require_wake_word
        self.callback: Optional[Callable[[str], Any]] = None

        self.response_handler: Optional[Callable[[Any], None]] = None

        self.idle_timeout_seconds = idle_timeout_seconds
        self._last_command_time: Optional[float] = None

        self._active = False
        self._active_lock = threading.Lock()

        self._cmd_queue: "queue.Queue[Optional[str]]" = queue.Queue()
        self._stop_event = threading.Event()
        self._capture_enabled = threading.Event()
        self._lifecycle_lock = threading.RLock()
        self._listen_timeout_seconds = 0.35
        self._phrase_time_limit_seconds = 12

        self._state = State.INACTIVE
        self._state_lock = threading.Lock()

        self.pause_listening_while_ai_busy = True

        try:
            if mic_index is not None:
                try:
                    self.microphone = sr.Microphone(device_index=mic_index)
                except Exception as e:
                    print(f"Selected microphone {mic_index} failed: {e}")
                    print("Falling back to default microphone...")
                    self.microphone = sr.Microphone()
            else:
                self.microphone = sr.Microphone()

            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
        except Exception as e:
            print(f"Microphone initialization failed: {e}")
            raise

        self.is_listening = False
        self._stt_thread: Optional[threading.Thread] = None
        self._worker_thread: Optional[threading.Thread] = None

    def _set_state(self, new_state: State) -> None:
        with self._state_lock:
            if self._state != new_state:
                self._state = new_state
                print(f"[STATE] -> {self._state.name}")

    def _get_state(self) -> State:
        with self._state_lock:
            return self._state

    def _set_active(self, value: bool) -> None:
        with self._active_lock:
            self._active = value

    def _is_active(self) -> bool:
        with self._active_lock:
            return self._active

    def _log_heard(self, text: str) -> None:
        print(f"[HEARD] {text}")

    def _log_info(self, text: str) -> None:
        print(f"[INFO] {text}")

    def _log_command(self, text: str) -> None:
        print(f"[COMMAND] {text}")

    def _log_ai_response(self, text: str) -> None:
        print(f"[AI RESPONSE] {text}")

    def set_callback(self, callback: Callable[[str], Any]) -> None:
        self.callback = callback

    def set_response_handler(self, handler: Callable[[Any], None]) -> None:
        """
        Set a handler that will be called during RESPONDING state.
        Use this if you want RESPONDING to appear before printing/TTS.
        """
        self.response_handler = handler

    def start(self) -> None:
        """Start STT producer + AI worker threads."""
        with self._lifecycle_lock:
            if self.is_listening:
                self._capture_enabled.set()
                if not self.require_wake_word:
                    self._activate()
                elif self._get_state() == State.SHUTTING_DOWN:
                    self._set_state(State.INACTIVE)
                return

            self.is_listening = True
            self._stop_event.clear()
            self._capture_enabled.set()
            self._set_active(False)
            self._set_state(State.INACTIVE)

            self._worker_thread = threading.Thread(target=self._ai_worker, daemon=True)
            self._stt_thread = threading.Thread(target=self._stt_loop, daemon=True)

            self._worker_thread.start()
            self._stt_thread.start()

    def set_capture_enabled(self, enabled: bool) -> None:
        """
        Fast mic toggle without tearing down worker threads.
        enabled=True  -> capture resumes immediately.
        enabled=False -> capture pauses immediately and state resets to INACTIVE.
        """
        with self._lifecycle_lock:
            if enabled and not self.is_listening:
                self.start()
                return

            if not self.is_listening:
                return

            if enabled:
                self._capture_enabled.set()
                if not self.require_wake_word:
                    self._activate()
                elif self._get_state() == State.SHUTTING_DOWN:
                    self._set_state(State.INACTIVE)
            else:
                self._capture_enabled.clear()
                self._set_active(False)
                if self._get_state() != State.SHUTTING_DOWN:
                    self._set_state(State.INACTIVE)

    def shutdown(self) -> None:
        """Gracefully stop threads and exit loops."""
        with self._lifecycle_lock:
            if not self.is_listening:
                return

            self._set_state(State.SHUTTING_DOWN)
            self._log_info("Shutting down...")

            self._capture_enabled.clear()
            self._stop_event.set()
            self._cmd_queue.put(None)

            stt_thread = self._stt_thread
            worker_thread = self._worker_thread

        current = threading.current_thread()
        if stt_thread and stt_thread.is_alive() and stt_thread is not current:
            stt_thread.join(timeout=2)
        if worker_thread and worker_thread.is_alive() and worker_thread is not current:
            worker_thread.join(timeout=2)

        with self._lifecycle_lock:
            self.is_listening = False
            self._stt_thread = None
            self._worker_thread = None
            self._set_active(False)
            self._set_state(State.INACTIVE)

    def test_microphone(self) -> bool:
        """Quick mic check: capture a short sample and run recognition."""
        try:
            print("🎙️ Testing microphone... say a few words.")
            with self.microphone as source:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=4)
            _ = self.recognizer.recognize_google(audio)
            print("✅ Microphone test passed.")
            return True
        except sr.WaitTimeoutError:
            print("❌ Mic test timed out (no speech detected).")
        except sr.UnknownValueError:
            print("❌ Mic test heard audio but couldn't understand it.")
        except sr.RequestError as e:
            print(f"❌ Speech API error during test: {e}")
        except Exception as e:
            print(f"❌ Mic test failed: {e}")
        return False

    @staticmethod
    def list_microphones():
        """List filtered microphones (real input devices only, deduplicated)."""
        pa = pyaudio.PyAudio()
        all_mics = sr.Microphone.list_microphone_names()

        filtered_mics = []
        seen_names = set()
        skip_keywords = [
            "stereo mix", "what u hear", "wave out mix", "loopback",
            "virtual", "output", "speakers", "realtek hd audio rear output",
            "realtek hd audio front output", "realtek digital output", "sound mapper",
            "primary sound", "voicemod", "steelseries sonar", "line out",
            "nvidia high definition"
        ]

        for i, name in enumerate(all_mics):
            name_lower = name.lower()

            if "iphone" in name_lower or "phone" in name_lower:
                clean_name = name.split('(')[0].strip()
                if clean_name.lower() not in seen_names:
                    seen_names.add(clean_name.lower())
                    filtered_mics.append((i, name))
                continue

            if any(keyword in name_lower for keyword in skip_keywords):
                continue

            try:
                info = pa.get_device_info_by_index(i)
                if info.get("maxInputChannels", 0) < 1:
                    continue
            except Exception:
                continue

            clean_name = name.split('(')[0].strip()
            if clean_name.lower() in seen_names:
                continue

            seen_names.add(clean_name.lower())
            filtered_mics.append((i, name))

        print("Available input microphones:")
        for idx, (_, name) in enumerate(filtered_mics):
            print(f"{idx+1}: {name}")

        pa.terminate()
        return filtered_mics

    def _stt_loop(self) -> None:
        """Producer: listens and enqueues commands."""
        while not self._stop_event.is_set():
            if not self._capture_enabled.is_set():
                time.sleep(0.03)
                continue
            try:
                with self.microphone as source:
                    while (
                        not self._stop_event.is_set()
                        and self._capture_enabled.is_set()
                    ):
                        if self.pause_listening_while_ai_busy:
                            st = self._get_state()
                            if st in (State.THINKING, State.RESPONDING):
                                time.sleep(0.05)
                                continue

                        self._maybe_deactivate_on_idle()

                        text = self._listen_for_phrase(source)
                        if not text:
                            continue

                        self._log_heard(text)

                        if "quit" in text.lower():
                            self.shutdown()
                            break

                        st = self._get_state()

                        if st == State.INACTIVE:
                            if self.require_wake_word:
                                extracted = self._extract_command_from_phrase(text)
                                if extracted is None:
                                    continue

                                self._activate()

                                cmd = extracted.strip()
                                if cmd:
                                    self._enqueue_command(cmd)
                                else:
                                    self._log_info("Activated. Listening...")
                            else:
                                self._activate()
                                self._enqueue_command(text)
                        elif st == State.LISTENING:
                            self._enqueue_command(text)
                        else:
                            pass

            except Exception as e:
                if not self._stop_event.is_set():
                    print(f"[ERROR] STT loop: {e}")
                time.sleep(0.1)

    def _ai_worker(self) -> None:
        """Consumer: processes commands sequentially."""
        while not self._stop_event.is_set():
            try:
                cmd = self._cmd_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            if cmd is None:
                self._cmd_queue.task_done()
                break

            if not self.callback:
                self._log_info("No callback set; dropping command.")
                self._cmd_queue.task_done()
                continue

            try:
                self._set_state(State.THINKING)
                result = self.callback(cmd) 

                self._set_state(State.RESPONDING)

                if self.response_handler is not None:
                    self.response_handler(result)
                else:
                    if isinstance(result, str) and result.strip():
                        self._log_ai_response(result)

            except Exception as e:
                print(f"[ERROR] AI worker: {e}")
            finally:
                if not self._stop_event.is_set() and self._get_state() != State.SHUTTING_DOWN:
                    self._set_state(State.LISTENING if self._is_active() else State.INACTIVE)

                self._cmd_queue.task_done()

        if not self._stop_event.is_set():
            self._set_state(State.INACTIVE)

    # ----------------- helpers -----------------
    def _activate(self) -> None:
        self._set_active(True)
        self._last_command_time = time.time()
        self._set_state(State.LISTENING)

    def _deactivate(self) -> None:
        self._set_active(False)
        self._last_command_time = None
        self._set_state(State.INACTIVE)
        if self.require_wake_word:
            self._log_info(
                f"Idle for {self.idle_timeout_seconds}s. Deactivated. Say '{self.wake_word}' again."
            )
        else:
            self._log_info(
                f"Idle for {self.idle_timeout_seconds}s. Deactivated. Speak to reactivate."
            )

    def _maybe_deactivate_on_idle(self) -> None:
        if not self._is_active():
            return
        if self._get_state() != State.LISTENING:
            return
        if self._last_command_time is None:
            return
        if not self._cmd_queue.empty():
            return
        if (time.time() - self._last_command_time) >= self.idle_timeout_seconds:
            self._deactivate()

    def _enqueue_command(self, text: str) -> None:
        cmd = text.strip()
        if not cmd:
            return

        self._last_command_time = time.time()
        self._log_command(cmd)
        self._cmd_queue.put(cmd)

    def _listen_for_phrase(self, source) -> Optional[str]:
        """Listen for a complete phrase."""
        try:
            if not self._capture_enabled.is_set() or self._stop_event.is_set():
                return None
            audio = self.recognizer.listen(
                source,
                timeout=self._listen_timeout_seconds,
                phrase_time_limit=self._phrase_time_limit_seconds,
            )
            return self.recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            return None
        except sr.WaitTimeoutError:
            return None
        except sr.RequestError as e:
            print(f"[ERROR] Speech recognition error: {e}")
            return None

    def _extract_command_from_phrase(self, text: str) -> Optional[str]:
        """If wake word is present, return text after wake word (may be empty). Else return None."""
        text_lower = text.lower()
        wake_words = ["hey quacky", "hey quaky", "quacky", "hey ducky"]

        for ww in wake_words:
            if ww in text_lower:
                pos = text_lower.find(ww)
                start = pos + len(ww)
                return text[start:].strip()
        return None


# ----------------- Example callback -----------------
def process_command(command: str) -> str:
    """
    Put Gemini call + (optional) TTS here.
    IMPORTANT: Keep this BLOCKING until you're done responding (including TTS playback)
    so STT stays paused during AI output (if pause_listening_while_ai_busy=True).
    """
    time.sleep(2)  
    response = f"Simulated response to: {command}"
    time.sleep(2)  
    return response


def main():
    print("🦆 Quacky Speech-to-Text")
    print("=" * 30)

    filtered_mics = QuackySpeechToText.list_microphones()

    if not filtered_mics:
        print("❌ No input microphones found. Using default.")
        mic_index = None
    else:
        print("\nSelect microphone:")
        print("0: Use default microphone")

        while True:
            try:
                choice = input(f"\nEnter microphone number 1-{len(filtered_mics)} (or 0 for default): ").strip()
                if choice == "" or choice == "0":
                    mic_index = None
                    break
                choice_int = int(choice)
                if 1 <= choice_int <= len(filtered_mics):
                    mic_index = filtered_mics[choice_int - 1][0]
                    break
                print(f"❌ Please enter a number between 1 and {len(filtered_mics)}, or 0 for default.")
            except ValueError:
                print("❌ Please enter a valid number.")

    print("\n" + "=" * 30)
    print("🎧 Listening... (Say 'quit' to exit)")
    print("=" * 30)

    stt: Optional[QuackySpeechToText] = None
    try:
        stt = QuackySpeechToText(mic_index=mic_index, idle_timeout_seconds=15)
        if not stt.test_microphone():
            print("❌ Microphone test failed. Please try a different microphone.")
            return

        stt.set_callback(process_command)
        stt.start()

        while stt.is_listening:
            time.sleep(0.2)

    except KeyboardInterrupt:
        if stt:
            stt.shutdown()
    except Exception as e:
        print(f"❌ Error: {e}")
        if stt:
            stt.shutdown()


if __name__ == "__main__":
    main()
