import sys
import sqlite3
from PyQt5.QtWidgets import QApplication, QMainWindow, QHeaderView, QTableWidgetItem, QCheckBox, QSpinBox
from PyQt5.QtGui import QIcon
from PyQt5 import uic
from config import *
import config


class Dialog(QMainWindow):

    def __init__(self, name, db_table, deps):
        super().__init__()

        uic.loadUi('interfaces/' + name + '.ui', self)
        self.setWindowTitle(name.capitalize())
        self.setStyleSheet(STYLESHEET)
        self.btn_save.clicked.connect(self.save)
        self.deps = deps

        con = sqlite3.connect(DATABASE_NAME)
        cur = con.cursor()

        res = cur.execute('SELECT * FROM ' + db_table)
        if name not in config.OBJECTS.keys():
            config.OBJECTS[name] = [self.new_object(i) for i in res]

        con.close()

    def new_object(self, params):
        obj = Obj(params[0])
        for i, attr in enumerate(self.deps.keys()):
            setattr(obj, attr, params[1 + i])
        return obj

    def show(self):
        super().show()
        self.manage('set')

    def save(self):
        if self.manage('get'):
            self.hide()
            windows['menu'].show()

    def manage(self, state):
        try:
            for attr in self.deps.keys():
                getattr(self, self.deps[attr][:2] + '_' + state)(getattr(self, self.deps[attr]), config.CHOSEN, attr)
            return True
        except AssertionError:
            print('Error')

    @staticmethod
    def cb_get(cb, obj, attr):
        setattr(obj, attr, cb.currentText())

    @staticmethod
    def cb_set(cb, obj, attr):
        if not hasattr(obj, attr):
            setattr(obj, attr, 1)
        cb.setCurrentIndex(int(getattr(obj, attr)) - 1)

    @staticmethod
    def tw_get(tw, obj, attr):
        keys = {
            'QCheckBox': 'isChecked',
            'QSpinBox': 'value'
        }
        out = []
        type_ = None
        tmp2 = []
        for i in range(tw.rowCount()):
            tmp = []
            for k in range(tw.columnCount()):
                if not type_ and tw.cellWidget(i, k).__class__.__name__ == 'QCheckBox':
                    type_ = 'bool'
                elif not type_ and tw.cellWidget(i, k).__class__.__name__ == 'QSpinBox':
                    type_ = 'number'
                if tw.cellWidget(i, k).__class__.__name__ != 'NoneType':
                    tmp.append('1' if getattr(tw.cellWidget(i, k), keys[tw.cellWidget(i, k).__class__.__name__])() else '0')
                else:
                    tmp.append(tw.item(i, k).text())
            tmp2.append('-'.join([str(j) for j in tmp]))
        out.append('_'.join(tmp2))
        out.append(tw.columnCount())
        out.append(type_)
        out.append('.' if attr == 'days' else attr)
        setattr(obj, attr, '|'.join([str(i) for i in out]))

    @staticmethod
    def tw_set(tw, obj, attr):
        set_stretch(tw)

        if not hasattr(obj, attr):
            gen = lambda name: '_'.join([str(i.name) + '-0' for i in config.OBJECTS[name]])
            keys = {
                'subjects': gen('subject') + '|2|number|subject',
                'asubjects': gen('subject') + '|2|bool|subject',
                'classes': gen('class') + '|2|bool|class',
                'rooms': gen('room') + '|2|bool|room',
                'days': '_'.join(['-'.join(['0' for _ in range(8)]) for _ in range(6)]) + '|8|bool|.'
            }
            setattr(obj, attr, keys[attr])
        values, x, type_, table = getattr(obj, attr).split('|')
        if not values:
            return

        values = [i.split('-') for i in values.split('_')]
        tw.setRowCount(len(values))
        keys = {
            'bool': [QCheckBox, 'setChecked'],
            'number': [QSpinBox, 'setValue']
        }
        for i in range(len(values)):
            if len(table) > 1:
                tw.setItem(i, 0, QTableWidgetItem(str(values[i][0])))
            for k in range(1 if len(table) > 1 else 0, tw.columnCount()):
                tw.setCellWidget(i, k, keys[type_][0]())
                getattr(tw.cellWidget(i, k), keys[type_][1])(int(values[i][k]))

    @staticmethod
    def le_get(le, obj, attr):
        assert le.text()
        setattr(obj, attr, le.text())

    @staticmethod
    def le_set(le, obj, attr):
        if not hasattr(obj, attr):
            setattr(obj, attr, '')
        le.setText(getattr(obj, attr))


class Menu(QMainWindow):

    def __init__(self):
        super().__init__()
        uic.loadUi('interfaces/menu.ui', self)
        self.setStyleSheet(STYLESHEET)
        self.setWindowTitle('Scheduler')

        self.tabWidget.currentChanged.connect(self.exit_)

        for name in config.OBJECTS.keys():
            getattr(self, 'btn_add_' + name).clicked.connect(self.add)
            getattr(self, 'tw_' + name).cellDoubleClicked.connect(self.add)
            set_stretch(getattr(self, 'tw_' + name))
            getattr(self, 'tw_' + name).hideColumn(0)
            getattr(self, 'btn_remove_' + name).clicked.connect(self.remove)

        self.deps = {
            0: None,
            1: 'class',
            2: 'teacher',
            3: 'subject',
            4: 'room'
        }
        self.show()

    def show(self):
        for name in config.OBJECTS.keys():
            getattr(self, 'tw_' + name).setRowCount(len(config.OBJECTS[name]))
            column = 1
            for attr in windows[name].deps.keys():
                if windows[name].deps[attr][:2] in ['le', 'cb']:
                    for i, obj in enumerate(config.OBJECTS[name]):
                        getattr(self, 'tw_' + name).setItem(i, column, QTableWidgetItem(str(getattr(obj, attr))))
                    column += 1
        super().show()

    def add(self, row):
        if isinstance(row, bool):
            ids = [i.id_ for i in config.OBJECTS[self.deps[self.tabWidget.currentIndex()]]]
            config.OBJECTS[self.deps[self.tabWidget.currentIndex()]].append(Obj(1 + max(ids) if ids else 0))
            row = -1
        config.CHOSEN = config.OBJECTS[self.deps[self.tabWidget.currentIndex()]][row]
        self.hide()
        windows[self.deps[self.tabWidget.currentIndex()]].show()

    def remove(self):
        pass

    def exit_(self):
        if self.tabWidget.currentIndex() == 5:
            # save to BD
            sys.exit(1)


def set_stretch(table):
    for i in range(table.columnCount()):
        table.horizontalHeader().setSectionResizeMode(i, QHeaderView.Stretch)
    for i in range(table.rowCount()):
        table.verticalHeader().setSectionResizeMode(i, QHeaderView.Stretch)


# temp for debugging
def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('icon.png'))

    windows = {
        'class': Dialog('class', 'Classes', {
            'name': 'le_name',
            'number': 'cb_number',
            'subjects': 'tw_subjects'
        }),
        'teacher': Dialog('teacher', 'Teachers', {
            'surname': 'le_surname',
            'name': 'le_name',
            'patronymic': 'le_patronymic',
            'classes': 'tw_classes',
            'asubjects': 'tw_asubjects',
            'rooms': 'tw_rooms',
            'days': 'tw_days'
        }),
        'subject': Dialog('subject', 'Subjects', {
            'name': 'le_name'
        }),
        'room': Dialog('room', 'Rooms', {
            'name': 'le_name'
        }),
    }

    sys.excepthook = except_hook  # temp for debugging
    windows['menu'] = Menu()
    sys.exit(app.exec())
