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
        self.btn_close.clicked.connect(self.close)
        self.deps = deps
        self.db_table = db_table

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
        self.statusBar().showMessage("")
        self.manage('set')

    def save(self):
        res = self.manage('get')
        if res:
            if config.CHOSEN_KEY[1] == -1:
                config.OBJECTS[config.CHOSEN_KEY[0]].append(res.copy())
            else:
                config.OBJECTS[config.CHOSEN_KEY[0]][config.CHOSEN_KEY[1]] = res.copy()
            self.hide()
            windows['menu'].show()

    def close(self):
        self.hide()
        windows['menu'].show()

    def manage(self, state):
        try:
            copy = config.CHOSEN_KEY[2].copy()
            for attr in self.deps.keys():
                getattr(self, self.deps[attr][:2] + '_' + state)(getattr(self, self.deps[attr]), copy, attr)
            return copy
        except AssertionError as e:
            self.statusBar().showMessage("Error: %s" % e)

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
        if attr == 'days':
            assert any([int(k) > 0 for i in tmp2 for k in i.split('-')]), 'table unfilled'
        else:
            assert any([int(i.split('-')[-1]) > 0 for i in tmp2]), 'table unfilled'
        out.append('_'.join(tmp2))
        out.append(tw.columnCount())
        out.append(type_)
        out.append('.' if attr == 'days' else attr)
        setattr(obj, attr, '|'.join([str(i) for i in out]))

    @staticmethod
    def tw_set(tw, obj, attr):
        set_stretch(tw)

        if attr == 'days':
            values = {str(i): str(k) for i, k in enumerate(getattr(obj, attr, '|').split('|')[0].replace('-', '_').split('_'))}
        else:
            values = {i.split('-')[0]: i.split('-')[1] for i in getattr(obj, attr, '|').split('|')[0].split('_') if i}
        gen = lambda name: {str(i.name): '0' for i in config.OBJECTS[name]}
        keys = {
            'subjects': (gen('subject'), '|1|number|subject'),
            'asubjects': (gen('subject'), '|1|bool|subject'),
            'classes': (gen('class'), '|1|bool|class'),
            'rooms': (gen('room'), '|1|bool|room'),
            'days': ({str(i): '0' for i in range(48)}, '|8|bool|.')
        }
        dictionary = keys[attr][0]
        if attr == 'days':
            setattr(obj, attr, '_'.join(['-'.join([values.get(str(k * 8 + i), dictionary[str(k * 8 + i)]) for i in range(8)]) for k in range(6)]) + '|8|bool|.')
        else:
            setattr(obj, attr, '_'.join([i + '-' + values.get(i, dictionary[i]) for i in dictionary.keys()]) + keys[attr][1])
        values, x, type_, table = getattr(obj, attr).split('|')
        if not values:
            return

        values = [i.split('-') for i in values.split('_')]
        tw.setRowCount(len(values))
        keys = {
            'bool': [QCheckBox, 'setChecked'],
            'number': [QSpinBox, 'setValue']
        }
        for i in range(tw.rowCount()):
            if len(table) > 1:
                tw.setItem(i, 0, QTableWidgetItem(str(values[i][0])))
            for k in range(1 if len(table) > 1 else 0, tw.columnCount()):
                tw.setCellWidget(i, k, keys[type_][0]())
                getattr(tw.cellWidget(i, k), keys[type_][1])(int(values[i][k]))

    @staticmethod
    def le_get(le, obj, attr):
        assert le.text(), 'line edit unfilled'
        setattr(obj, attr, le.text())

    @staticmethod
    def le_set(le, obj, attr):
        if not hasattr(obj, attr):
            setattr(obj, attr, '')
        le.setText(str(getattr(obj, attr)))


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
            column = 0
            for attr in ['id_', *windows[name].deps.keys()]:
                if attr == 'id_' or windows[name].deps[attr][:2] in ['le', 'cb']:
                    for i, obj in enumerate(config.OBJECTS[name]):
                        getattr(self, 'tw_' + name).setItem(i, column, QTableWidgetItem(str(getattr(obj, attr))))
                    column += 1
        super().show()

    def add(self, row):
        if isinstance(row, bool):
            ids = [i.id_ for i in config.OBJECTS[self.deps[self.tabWidget.currentIndex()]]]
            row = -1
            obj = Obj(max(ids) + 1 if ids else 0)
        else:
            obj = config.OBJECTS[self.deps[self.tabWidget.currentIndex()]][row]

        config.CHOSEN_KEY = (self.deps[self.tabWidget.currentIndex()], row, obj)
        self.hide()
        windows[self.deps[self.tabWidget.currentIndex()]].show()

    def remove(self):
        i = 0
        while i < len(config.OBJECTS[self.deps[self.tabWidget.currentIndex()]]):
            if config.OBJECTS[self.deps[self.tabWidget.currentIndex()]][i].id_ in [int(getattr(self, 'tw_' + self.deps[self.tabWidget.currentIndex()]).item(i, 0).text()) for i in list(set([idx.row() for idx in getattr(self, 'tw_' + self.deps[self.tabWidget.currentIndex()]).selectedIndexes()]))]:
                config.OBJECTS[self.deps[self.tabWidget.currentIndex()]].remove(config.OBJECTS[self.deps[self.tabWidget.currentIndex()]][i])
                i -= 1
            i += 1
        self.show()

    def exit_(self):
        if self.tabWidget.currentIndex() == 5:
            con = sqlite3.connect(DATABASE_NAME)
            cur = con.cursor()
            for window in windows.keys():
                if not isinstance(windows[window], Dialog):
                    continue
                cur.execute("DELETE FROM " + windows[window].db_table)
                for obj in config.OBJECTS[window]:
                    cur.execute('INSERT INTO ' + windows[window].db_table + '(' + ', '.join([str(i) for i in windows[window].deps.keys()]) +') VALUES(' + ', '.join(["'" + str(getattr(obj, i)) + "'" for i in [str(k) for k in windows[window].deps.keys()]])+')')
            con.commit()
            con.close()
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
    # заблокировать крестик
    # учесть ситуацию выхода из диалога - надо удалять OBJECTS[window][-1]
    sys.excepthook = except_hook  # temp for debugging
    windows['menu'] = Menu()
    sys.exit(app.exec())
