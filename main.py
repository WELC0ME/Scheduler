import sys
import sqlite3
from typing import Dict, Union

from PyQt5.QtWidgets import QApplication, QMainWindow, QHeaderView, QTableWidgetItem, QCheckBox, QSpinBox
from PyQt5.QtGui import QIcon
from PyQt5 import uic
from PyQt5.QtCore import Qt
from config import *
import config
import datetime
import os
import shutil
from docx import Document


class Dialog(QMainWindow):

    def __init__(self, name, db_table, deps):
        super().__init__()

        uic.loadUi('interfaces/' + name + '.ui', self)
        self.setWindowTitle(name.capitalize())
        self.setStyleSheet(STYLESHEET)
        self.btn_save.clicked.connect(self.save)
        self.btn_close.clicked.connect(self.close)
        self.db_table = db_table
        self.deps = deps
        self.copy = None

        con = sqlite3.connect(DATABASE_NAME)
        cur = con.cursor()
        config.OBJECTS[name] = [self.new_object(i) for i in cur.execute('SELECT * FROM ' + db_table)]
        con.close()

    def new_object(self, params):
        obj = Obj(params[0])
        for i, attr in enumerate(self.deps.keys()):
            try:
                setattr(obj, attr, eval(str(params[1 + i])))
            except Exception:
                setattr(obj, attr, eval('"' + str(params[1 + i]) + '"'))
        return obj

    def show(self):
        super().show()
        self.statusBar().showMessage("")
        self.manage('set')

    def save(self):
        if self.manage('get'):
            if config.CHOSEN_KEY[1] == -1:
                config.OBJECTS[config.CHOSEN_KEY[0]].append(self.copy.copy())
            else:
                config.OBJECTS[config.CHOSEN_KEY[0]][config.CHOSEN_KEY[1]] = self.copy.copy()
            self.copy = None
            self.hide()
            windows['menu'].show()

    def close(self):
        self.copy = None
        self.hide()
        windows['menu'].show()

    def manage(self, state):
        try:
            self.copy = config.CHOSEN_KEY[2].copy() if not self.copy else self.copy
            for attr in self.deps.keys():
                getattr(self, self.deps[attr][:2] + '_' + state)(getattr(self, self.deps[attr]), self.copy, attr)
            return True
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
        out = getattr(obj, attr)
        values = list(getattr(obj, attr)['values'].keys())
        columns = [i for i in range(tw.columnCount())] if attr == 'days' else [1]
        for i in range(tw.rowCount()):
            for k in columns:
                res = getattr(tw.cellWidget(i, k), keys[str(type(tw.cellWidget(i, k))).split('.')[-1][:-2]])()
                if isinstance(res, bool):
                    res = 1 if res else 0
                shift = k if attr == 'days' else 0
                coeff = tw.columnCount() if attr == 'days' else 1
                out['values'][values[i * coeff + shift]] = res
        setattr(obj, attr, out)

    @staticmethod
    def tw_set(tw, obj, attr):
        set_stretch(tw)

        gen = lambda name: {i.id_: 0 for i in config.OBJECTS[name]}
        keys = {
            'subjects': {'values': gen('subject'), 'type': 'number', 'table': 'subject'},
            'asubjects': {'values': gen('subject'), 'type': 'bool', 'table': 'subject'},
            'classes': {'values': gen('class'), 'type': 'bool', 'table': 'class'},
            'rooms': {'values': gen('room'), 'type': 'bool', 'table': 'room'},
            'days': {'values': {i: 0 for i in range(48)}, 'type': 'bool', 'table': '.'},
        }
        res = keys[attr]
        for i in res['values'].keys():
            try:
                res['values'][i] = getattr(obj, attr)['values'][i]
            except Exception:
                continue
        setattr(obj, attr, res)

        keys = {
            'bool': [QCheckBox, 'setChecked'],
            'number': [QSpinBox, 'setValue']
        }

        tw.setRowCount(len(res['values'].keys()) if attr != 'days' else 6)
        values = list(res['values'].keys())
        if attr != 'days':
            for i in range(tw.rowCount()):
                tw.setItem(i, 0, QTableWidgetItem(str([j for j in config.OBJECTS[res['table']] if j.id_ == values[i]][0].name)))
                tw.setCellWidget(i, 1, keys[res['type']][0]())
                getattr(tw.cellWidget(i, 1), keys[res['type']][1])(res['values'][values[i]])
        else:
            for i in range(tw.rowCount()):
                for k in range(tw.columnCount()):
                    tw.setCellWidget(i, k, keys[res['type']][0]())
                    getattr(tw.cellWidget(i, k), keys[res['type']][1])(res['values'][values[i * tw.columnCount() + k]])

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

        flags = self.windowFlags() | Qt.FramelessWindowHint
        self.setWindowFlags(flags)

        self.tabWidget.currentChanged.connect(self.exit_)
        self.btn_create.clicked.connect(self.create_schedule)

        for name in config.OBJECTS.keys():
            getattr(self, 'btn_add_' + name).clicked.connect(self.add)
            getattr(self, 'tw_' + name).cellDoubleClicked.connect(self.add)
            set_stretch(getattr(self, 'tw_' + name))
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
            for attr in windows[name].deps.keys():
                if windows[name].deps[attr][:2] in ['le', 'cb']:
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
        objects = config.OBJECTS[self.deps[self.tabWidget.currentIndex()]]
        for k in sorted(list(set([idx.row() for idx in getattr(self, 'tw_' + self.deps[self.tabWidget.currentIndex()]).selectedIndexes()])))[::-1]:
            objects.remove(objects[k])
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
                    cur.execute('INSERT INTO ' + windows[window].db_table + '(' + ', '.join(['id', *[str(i) for i in windows[window].deps.keys()]]) +') VALUES (' + ', '.join(['"' + str(getattr(obj, i)) + '"' for i in [str(k) for k in ['id_', *windows[window].deps.keys()]]]) + ')')
            con.commit()
            con.close()
            sys.exit(1)

    def create_schedule(self):
        table = []
        for day in range(6 * 8):
            table.append([])
            for class_ in config.OBJECTS['class']:
                table[day].append([])
                for teacher in config.OBJECTS['teacher']:
                    if teacher.days['values'][day] and teacher.classes['values'][class_.id_]:
                        for room_id in [i for i in list(teacher.rooms['values'].keys()) if teacher.rooms['values'][i]]:
                            for subject_id in [i for i in list(teacher.asubjects['values'].keys()) if teacher.asubjects['values'][i]]:
                                groups_ = [obj_.groups for obj_ in config.OBJECTS['subject'] if obj_.id_ == subject_id][0]
                                table[day][-1].append((subject_id, teacher.id_, room_id, groups_))
        table.append([])
        for class_ in config.OBJECTS['class']:
            table[-1].append({})
            for subject in list(class_.subjects['values'].keys()):
                table[-1][-1][subject] = class_.subjects['values'][subject]

        config.SOLVED = False
        config.RESULT = []
        try:
            self.solve(table, 0, 0)
        except Exception:
            config.SOLVED = False
            config.RESULT = []

        if config.SOLVED:
            try:
                message = 'Success'

                classes = {i: k for i, k in enumerate(config.OBJECTS['class'])}
                subjects = {i.id_: i for i in config.OBJECTS['subject']}
                teachers = {i.id_: i for i in config.OBJECTS['teacher']}
                rooms = {i.id_: i for i in config.OBJECTS['room']}

                shutil.rmtree('Schedule', ignore_errors=True)
                os.mkdir('Schedule')
                tmp_classes = {}
                tmp_teachers = {}
                for lesson, i in enumerate(table[:-1]):
                    for class_, k in enumerate(i):
                        if k:
                            if class_ not in tmp_classes.keys():
                                tmp_classes[class_] = []
                            for m in range(len(k)):
                                tmp_classes[class_].append((lesson, k[m][0], k[m][1], k[m][2]))
                            for m in range(len(k)):
                                if k[m][1] not in tmp_teachers.keys():
                                    tmp_teachers[k[m][1]] = []
                            class_id = config.OBJECTS['class'][class_].id_
                            for m in range(len(k)):
                                tmp_teachers[k[m][1]].append((lesson, k[m][0], class_id, k[m][2]))

                self.save('Classes', subjects, rooms, classes, teachers, tmp_classes)
                self.save('Teachers', subjects, rooms, teachers, classes, tmp_teachers)
            except Exception:
                message = 'Fail'
        else:
            message = 'Fail'
        time = '[' + str(datetime.datetime.now()).split('.')[0].split()[1] + '] '
        self.log.setPlainText(self.log.toPlainText() + time + message + '\n')

    def save(self, path, subjects, rooms, s_list, a_list, values):
        os.mkdir('Schedule/' + path)
        for id_ in list(values.keys()):
            current = s_list[id_]
            if hasattr(current, 'surname'):
                name = ' '.join([
                    str(current.surname),
                    str(current.name),
                    str(current.patronymic)
                ])
            else:
                name = str(current.name)
            document = Document()

            document.add_heading(str(name), 0)
            table = document.add_table(rows=7, cols=9)

            week_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

            for i in range(1, 9):
                table.rows[0].cells[i].text = str(i - 1)
            for i in range(6):
                table.rows[1 + i].cells[0].text = week_days[i]

            for lesson in values[id_]:
                row, col = lesson[0] // 8 + 1, lesson[0] % 8 + 1
                cells = table.rows[row].cells
                if hasattr(a_list[lesson[2]], 'surname'):
                    add_name = ' '.join([
                        str(a_list[lesson[2]].surname),
                        str(a_list[lesson[2]].name),
                        str(a_list[lesson[2]].patronymic)
                    ])
                else:
                    add_name = str(a_list[lesson[2]].name)
                cells[col].text += ' ' .join([
                    str(subjects[lesson[1]].name),
                    add_name,
                    str(rooms[lesson[3]].name),
                ]) + '\n'
            document.save('Schedule/' + path + '/' + name + '.docx')

    def solve(self, table, lesson, class_):
        if config.SOLVED:
            return
        if class_ == len(table[lesson]):
            class_ = 0
            lesson += 1
        if lesson + 1 > 6 * 8:
            if all([all([j == 0 for j in k.values()]) for k in table[-1]]):
                config.RESULT = self.copy_table(table)
                config.SOLVED = True
            return

        for i in range(len(table[-1])):
            targets = table[-1][i]
            for j in targets.keys():
                lesson_counter = 0
                for k in range(len(table) - 1):
                    lesson_counter += 1 if len([h for h in table[k][i] if h[0] == j]) >= 1 else 0
                if lesson_counter < targets[j]:
                    return

        continuing = False
        for i in table[lesson][class_]:

            if table[-1][class_][i[0]] > 0:
                out = self.copy_table(table)
                av_teachers = [j for j in table[lesson][class_] if j[0] == i[0]]
                i = (i[0], i[1], i[2], int(i[3]))
                if len(av_teachers) < i[3]:
                    continue
                continuing = True
                out[lesson][class_] = av_teachers[:i[3]]
                out[-1][class_][i[0]] -= 1

                for k in range(class_ + 1, len(out[lesson])):
                    for j in out[lesson][k]:
                        if j[1] in [m[1] for m in out[lesson][class_]] or j[2] in [m[2] for m in out[lesson][class_]]:
                            out[lesson][k].remove(j)

                for k in range(lesson + 1, len(out) - 1):
                    for j in out[k][class_]:
                        if j[0] in [m[0] for m in out[lesson][class_]] and j[1] not in [m[1] for m in out[lesson][class_]]:
                            out[k][class_].remove(j)
                        if out[-1][class_][i[0]] == 0 and j[0] in [m[0] for m in out[lesson][class_]]:
                            out[k][class_].remove(j)

                self.solve(out, lesson, class_ + 1)

        if not continuing:
            out = self.copy_table(table)
            out[lesson][class_] = []
            self.solve(out, lesson, class_ + 1)

    def copy_table(self, table):
        return [[table[i][k] for k in range(len(table[i]))] for i in range(len(table))]


def set_stretch(table):
    for i in range(table.columnCount()):
        table.horizontalHeader().setSectionResizeMode(i, QHeaderView.Stretch)
    for i in range(table.rowCount()):
        table.verticalHeader().setSectionResizeMode(i, QHeaderView.Stretch)


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
            'name': 'le_name',
            'groups': 'cb_groups'
        }),
        'room': Dialog('room', 'Rooms', {
            'name': 'le_name'
        }),
    }
    windows['menu'] = Menu()
    sys.exit(app.exec())
