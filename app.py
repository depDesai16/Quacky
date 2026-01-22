import time
print("Starting delete subroutine!")
for i in range(1000):
    time.sleep(0.1)
    if i == 500:
        print("50% complete!")
    print(i)
print("Deletions complete, thank you for your patience.")
exit

