from time import sleep, time
# from keyboard import is_pressed
from cotps import Client
from _credentials import USERNAME, PASSWORD


if __name__ == '__main__':

    # with Client(username=USERNAME, pwd=PASSWORD) as client:
    #     current_balance = client.get_balance()
    #     print("Current balance is", current_balance)

    #     while is_pressed('q') == False:
    #         new_balance = client.make_transactions()
    #         print("New balance is", new_balance)
    #         sleep(30)
    
    # first time
    with Client(username=USERNAME, pwd=PASSWORD) as client:
            balance = client.make_transactions()
            print("Start balance is", balance)

    # more times
    start = time()
    # while is_pressed('q') == False:
    while True:
        if time() - start > 60.0:
            start = time()
            with Client(username=USERNAME, pwd=PASSWORD) as client:
                balance = client.make_transactions()
                print("Balance is now", balance)
            sleep(0.25)