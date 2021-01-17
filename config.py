RESULT = []
SOLVED = False
STYLESHEET = open('data/styles.stylesheet', 'r').read()
DATABASE_NAME = 'data/School.db'
OBJECTS = {}
CHOSEN = None


class Obj:

    def __init__(self, id_):
        self.id_ = id_
