#hahaha takes any amount of arguments and returns the sum of all the arguments that are integers and not less than 0

def hahaha(*arghehe):
    hello = 0
    def haha(*args):
        nonlocal hello
        for hehe in (args):
            if not isinstance(hehe, int) or hehe <= 0:
                break
            hello += 1
            haha(hehe - 1)
    haha(*arghehe)
    return hello