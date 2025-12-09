#Vehicle class for use with Parking Lot Manager
class Vehicle:
    def __init__(self,regnum,make,model,color):
        self.color = color
        self.regnum = regnum
        self.make = make
        self.model = model

    def getMake(self):
        return self.make

    def getModel(self):
        return self.model

    def getColor(self):
        return self.color

    def getRegNum(self):
        return self.regnum

class Car(Vehicle):

    def __init__(self,regnum,make,model,color):
        Vehicle.__init__(self,regnum,make,model,color)

    def getType(self):
        return "Car"

class Truck(Vehicle):

    def __init__(self,regnum,make,model,color):
        Vehicle.__init__(self,regnum,make,model,color)

    def getType(self):
        return "Truck"


class Motorcycle(Vehicle):

    def __init__(self,regnum,make,model,color):
        Vehicle.__init__(self,regnum,make,model,color)

    def getType(self):
        return "Motorcycle"


class Bus(Vehicle):

    def __init__(self,regnum,make,model,color):
        Vehicle.__init__(self,regnum,make,model,color)

    def getType(self):
        return "Bus"



