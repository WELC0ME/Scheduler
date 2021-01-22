RESULT = []
SOLVED = False
STYLESHEET = open('data/styles.stylesheet', 'r').read()
DATABASE_NAME = 'data/School.db'
OBJECTS = {}
CHOSEN_KEY = None
SOLVED = False
RESULT = []


class Obj:

    def __init__(self, id_):
        self.id_ = id_

    def copy(self):
        out = Obj(self.id_)
        for i in self.__dict__.keys():
            setattr(out, i, self.__dict__[i])
        return out
