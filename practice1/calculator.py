class Calculator:
    def arithmatic(self, num1, num2, request):
        if request == "plus":
            return num1 + num2
        if request == "minus":
            return num1 - num2
        if request == "times":
            return num1 * num2
        if request == "divide":
            while num2 == 0:
                return ValueError
            return num1 / num2
        else:
            raise ValueError