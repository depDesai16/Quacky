import sys
import os

# Add BOTH the root and the frontend folder to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend"))

import frontend

frontend.run_it()