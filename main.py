import sys
import sqlite3
from docx import Document
from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow, QCheckBox, \
    QTableWidgetItem, QSpinBox, QHeaderView
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon


class IncorrectInputError(Exception):
    pass


RESULT = []
SOLVED = False
STYLESHEET = open('styles.stylesheet', 'r').read()
DATABASE_NAME = 'School.db'


def create_schedule():
    global RESULT, SOLVED
    if SOLVED:
        return

    con = sqlite3.connect(DATABASE_NAME)
    cur = con.cursor()

    subjects = cur.execute("SELECT id FROM Subjects").fetchall()
    classes = cur.execute("SELECT id, subjects FROM Classes").fetchall()
    teachers = cur.execute(
        "SELECT id, subject, classes, work_hours FROM Teachers").fetchall()
    con.close()

    subjects_transition = {subjects[i][0]: i for i in range(len(subjects))}

    teachers_transition = {teachers[i][0]: i for i in range(len(teachers))}

    table = []
    for i in range(6 * 8):
        table.append([])
        for k in range(len(classes)):
            table[i].append([])
            for j in range(len(teachers)):

                if teachers[j][3][i] == '1' and str(classes[k][0]) in \
                        teachers[j][2].split():
                    table[i][k].append((subjects_transition[teachers[j][1]],
                                        teachers_transition[teachers[j][0]]))

    table.append([])
    for class_ in classes:
        tmp = []
        subject_counter = 0
        for i in subjects_transition.keys():

            if str(i) in class_[1].split()[::2]:
                tmp.append(int(class_[1].split()[class_[1].split()[::2].index(
                    str(i)) * 2 + 1]))
                subject_counter += 1

                if subject_counter == len(class_[1].split()[::2]):
                    break
            else:
                tmp.append(0)

        table[-1].append(tmp[:])

    RESULT = []
    if any([i for i in table]):
        solve(table, 0, 0)

    if SOLVED:
        menu.warning.hide()
        menu.tabWidget_2.show()

        menu.statusBar().showMessage('Schedule has been successfully created',
                                     2000)
    else:
        menu.statusBar().showMessage('Failed to make a schedule', 2000)


def copy_table(table):
    return [[table[i][k][:] for k in range(len(table[i]))] for i in
            range(len(table))]


def solve(table, lesson, class_):
    global RESULT, SOLVED
    if SOLVED:
        return
    if class_ == len(table[lesson]):
        class_ = 0
        lesson += 1
    if lesson + 1 > 6 * 8:
        if all([sum(k) == 0 for k in table[-1]]):
            RESULT = copy_table(table)
            SOLVED = True
        return

    for i in range(len(table[-1])):
        for k in range(len(table[-1][i])):

            probably_lessons = 0
            for j in range(6 * 8):
                for u in range(len(table[j][i])):
                    if table[j][i][u][0] == k:
                        probably_lessons += 1

            if probably_lessons < table[-1][i][k]:
                return

    continuing = False

    for i in range(len(table[lesson][class_])):
        out = copy_table(table)

        if out[lesson][class_][i][0] < len(out[-1][class_]) and \
                out[-1][class_][out[lesson][class_][i][0]] > 0:
            continuing = True

            out[-1][class_][out[lesson][class_][i][0]] -= 1

            for k in range(class_ + 1, len(out[lesson])):
                if out[lesson][class_][i] in out[lesson][k]:
                    out[lesson][k].remove(out[lesson][class_][i])

            for k in range(lesson + 1, 6 * 8):
                tmp = []
                for j in range(len(out[k][class_])):
                    if out[k][class_][j][1] == out[lesson][class_][i][1] or \
                            out[k][class_][j][0] != out[lesson][class_][i][0]:
                        tmp.append(out[k][class_][j])
                out[k][class_] = tmp[:]

            out[lesson][class_] = [out[lesson][class_][i]]
            solve(out, lesson, class_ + 1)

    if not continuing:
        out = copy_table(table)
        out[lesson][class_] = []
        solve(out, lesson, class_ + 1)


def set_stretch(table):
    for i in range(table.columnCount()):
        table.horizontalHeader().setSectionResizeMode(i, QHeaderView.Stretch)
    for i in range(table.rowCount()):
        table.verticalHeader().setSectionResizeMode(i, QHeaderView.Stretch)


def line_edit_interaction(line_edit, table, row, column):
    if not isinstance(row, bool):
        line_edit.setText(table.item(row, column).text())
    else:
        line_edit.setText('')


class MainMenu(QMainWindow):

    def __init__(self):
        super().__init__()
        uic.loadUi('main_menu.ui', self)
        self.setStyleSheet(STYLESHEET)
        self.setWindowTitle('Scheduler')

        self.btn_exit.clicked.connect(lambda: sys.exit(1))
        self.btn_create.clicked.connect(create_schedule)

        self.btn_subjects_add.clicked.connect(self.show_info)
        self.btn_subjects_remove.clicked.connect(self.remove)
        self.table_subjects.cellDoubleClicked.connect(self.show_info)

        self.btn_teachers_add.clicked.connect(self.show_info)
        self.btn_teachers_remove.clicked.connect(self.remove)
        self.table_teachers.cellDoubleClicked.connect(self.show_info)

        self.btn_classes_add.clicked.connect(self.show_info)
        self.btn_classes_remove.clicked.connect(self.remove)
        self.table_classes.cellDoubleClicked.connect(self.show_info)

        self.table_by_teachers.cellDoubleClicked.connect(self.show_info)
        self.table_by_classes.cellDoubleClicked.connect(self.show_info)

        self.table_requests = {
            self.table_subjects: 'SELECT id, title FROM Subjects',
            self.table_teachers: """SELECT Teachers.id, Teachers.surname,
                                Teachers.name, Teachers.patronymic,
                                Subjects.title FROM Teachers JOIN Subjects On
                                Teachers.subject = Subjects.id""",
            self.table_classes: 'SELECT id, name, number FROM Classes',
            self.table_by_classes: self.table_classes,
            self.table_by_teachers: self.table_teachers}

        for table in self.table_requests.keys():
            set_stretch(table)

        self.tabWidget_2.hide()
        self.load()

    def load(self):

        con = sqlite3.connect(DATABASE_NAME)
        cur = con.cursor()

        for table in self.table_requests.keys():
            table.hideColumn(0)
            table.setRowCount(0)
            if not isinstance(self.table_requests[table], str):
                self.table_requests[table] = self.table_requests[
                    self.table_requests[table]]

            for i, row in enumerate(
                    cur.execute(self.table_requests[table]).fetchall()):
                table.setRowCount(table.rowCount() + 1)
                for k, elem in enumerate(row):
                    table.setItem(i, k, QTableWidgetItem(str(elem)))

        con.close()

    def remove(self):

        global SOLVED
        SOLVED = False
        menu.tabWidget_2.hide()
        menu.warning.show()

        translation = {
            self.btn_subjects_remove: ['Subjects', self.table_subjects],
            self.btn_teachers_remove: ['Teachers', self.table_teachers],
            self.btn_classes_remove: ['Classes', self.table_classes]}
        con = sqlite3.connect(DATABASE_NAME)
        cur = con.cursor()

        for i in sorted(list(set([
            i.row() for i in translation[self.sender()][1].selectedIndexes()
        ])))[::-1]:

            cur.execute("DELETE FROM " + translation[self.sender()][
                0] + " WHERE id = ?",
                        (translation[self.sender()][1].item(i, 0).text(),))

            if translation[self.sender()][0] == 'Subjects':
                cur.execute("DELETE FROM Teachers WHERE subject = ?",
                            (translation[self.sender()][1].item(i, 0).text(),))
                classes = cur.execute(
                    "SELECT id, subjects FROM Classes").fetchall()

                for k in range(len(classes)):
                    new_subjects = [int(j) for j in classes[k][1].split()]

                    if int(translation[
                               self.sender()
                           ][1].item(i, 0).text()) in new_subjects:
                        ind = new_subjects.index(int(
                            translation[self.sender()][1].item(i, 0).text()))
                        new_subjects.remove(new_subjects[ind])
                        new_subjects.remove(new_subjects[ind])

                        new_subjects = ' '.join([str(j) for j in new_subjects])

                        cur.execute(
                            "UPDATE Classes SET subjects = ? WHERE id = ?",
                            (new_subjects, classes[k][0]))

            elif translation[self.sender()][0] == 'Classes':
                teachers = cur.execute(
                    "SELECT id, classes FROM Teachers").fetchall()
                for k in range(len(teachers)):
                    new_classes = [int(j) for j in teachers[k][1].split()]

                    if translation[
                        self.sender()
                    ][1].item(i, 0).text() in new_classes:
                        new_classes.remove(
                            translation[self.sender()][1].item(i, 0).text())

                    new_classes = ' '.join([st(j) for j in new_classes])

                    cur.execute("UPDATE Teachers SET classes = ? WHERE id = ?",
                                (new_classes, teachers[k][0]))

        con.commit()
        con.close()

        self.load()

    def show_info(self, row):

        translation = {self.btn_subjects_add: subject_dialog,
                       self.table_subjects: subject_dialog,
                       self.btn_teachers_add: teacher_dialog,
                       self.table_teachers: teacher_dialog,
                       self.btn_classes_add: class_dialog,
                       self.table_classes: class_dialog,
                       self.table_by_teachers: timetable_view,
                       self.table_by_classes: timetable_view}
        translation[self.sender()].show_info(row)


class Dialog(QMainWindow):

    def __init__(self, ui_name):
        super().__init__()
        uic.loadUi(ui_name, self)
        self.setStyleSheet(STYLESHEET)
        self.btn_save.clicked.connect(self.save)
        self.current_id = None

    def show_info(self, row):

        self.statusBar().showMessage('')
        if not isinstance(row, bool):
            self.current_id = self.table.item(row, 0).text()
        else:
            if self.table.rowCount() != 0:
                self.current_id = int(
                    self.table.item(self.table.rowCount() - 1, 0).text()) + 1
            else:
                self.current_id = 0

    def save(self):

        global SOLVED
        try:
            con = sqlite3.connect(DATABASE_NAME)
            cur = con.cursor()
            values = self.get_values()

            cur.execute("DELETE FROM " + self.table_name + " WHERE id = ?",
                        (self.current_id,))
            cur.execute("SELECT * FROM " + self.table_name).fetchone()
            headers = [i[0] for i in cur.description]
            cur.execute(
                """INSERT INTO """ + self.table_name + """(""" + ', '.join(
                    headers) +
                """) VALUES(""" + '?, ' * (len(headers) - 1) + """?)""",
                (self.current_id, *values))

            con.commit()
            con.close()

            menu.load()
            SOLVED = False
            menu.tabWidget_2.hide()
            menu.warning.show()
            self.hide()
        except IncorrectInputError as e:
            self.statusBar().showMessage("Error: %s" % e)


class SubjectDialog(Dialog):

    def __init__(self):
        super().__init__('subject_dialog.ui')
        self.setWindowTitle('Subject')

        self.table = menu.table_subjects
        self.table_name = 'Subjects'

    def show_info(self, row):

        super().show_info(row)
        line_edit_interaction(self.le_title, self.table, row, 1)
        self.show()

    def get_values(self):

        if self.le_title.text() == '':
            raise IncorrectInputError('field title is empty')

        con = sqlite3.connect(DATABASE_NAME)
        cur = con.cursor()
        subjects = [i[0] for i in
                    cur.execute("SELECT title FROM subjects").fetchall()]
        con.close()

        if self.le_title.text() in subjects:
            raise IncorrectInputError(
                'subject with the same name already exists')

        return [self.le_title.text()]


class TeacherDialog(Dialog):

    def __init__(self):
        super().__init__('teacher_dialog.ui')
        self.setWindowTitle('Teacher')

        self.table = menu.table_teachers
        self.table_name = 'Teachers'

        self.table_available_classes.hideColumn(0)
        set_stretch(self.table_available_classes)
        set_stretch(self.table_work_hours)

    def show_info(self, row):

        super().show_info(row)
        con = sqlite3.connect(DATABASE_NAME)
        cur = con.cursor()

        subjects = [i[0] for i in
                    cur.execute("SELECT title FROM Subjects").fetchall()]
        self.cb_subject.clear()
        self.cb_subject.addItems(subjects)
        if not isinstance(row, bool):
            self.cb_subject.setCurrentIndex(
                subjects.index(self.table.item(row, 4).text()))

        classes = [[str(i[0]), i[1]] for i in
                   cur.execute("SELECT id, name FROM Classes").fetchall()]

        current_teacher = cur.execute("SELECT * FROM Teachers WHERE id = ?",
                                      (self.current_id,)).fetchone()
        con.close()

        self.table_available_classes.setRowCount(0)
        for i in range(len(classes)):

            self.table_available_classes.setRowCount(
                self.table_available_classes.rowCount() + 1)
            self.table_available_classes.setItem(i, 0, QTableWidgetItem(
                str(classes[i][0])))
            self.table_available_classes.setItem(i, 1, QTableWidgetItem(
                str(classes[i][1])))

            self.table_available_classes.setCellWidget(i, 2, QCheckBox(self))

            if current_teacher and classes[i][0] in current_teacher[5].split():
                self.table_available_classes.cellWidget(i, 2).setCheckState(
                    Qt.Checked)

        for i in range(6):
            for k in range(8):
                tmp_cb = QCheckBox(self)
                if current_teacher and current_teacher[6][i * 8 + k] == '1':
                    tmp_cb.setCheckState(Qt.Checked)
                self.table_work_hours.setCellWidget(i, k, tmp_cb)

        line_edit_interaction(self.le_surname, self.table, row, 1)
        line_edit_interaction(self.le_name, self.table, row, 2)
        line_edit_interaction(self.le_patronymic, self.table, row, 3)

        self.show()

    def get_values(self):

        if self.le_surname.text() == '':
            raise IncorrectInputError('field surname is empty')

        if self.le_name.text() == '':
            raise IncorrectInputError('field name is empty')

        if self.le_patronymic.text() == '':
            raise IncorrectInputError('field patronymic is empty')

        con = sqlite3.connect(DATABASE_NAME)
        cur = con.cursor()
        subjects = cur.execute("SELECT id FROM subjects").fetchall()
        con.close()

        str_classes = ''
        for i in range(self.table_available_classes.rowCount()):
            if self.table_available_classes.cellWidget(i, 2).isChecked():
                str_classes += self.table_available_classes.item(i,
                                                                 0).text() + \
                               ' '

        str_work_hours = ''
        for i in range(self.table_work_hours.rowCount()):
            for k in range(self.table_work_hours.columnCount()):

                if self.table_work_hours.cellWidget(i, k).isChecked():
                    str_work_hours += '1'
                else:
                    str_work_hours += '0'

        if str_classes == '':
            raise IncorrectInputError('no classes')

        if len(set(str_work_hours)) == 1:
            raise IncorrectInputError('no work hours')

        return [self.le_surname.text(),
                self.le_name.text(),
                self.le_patronymic.text(),
                subjects[self.cb_subject.currentIndex()][0],
                str_classes,
                str_work_hours]


class ClassDialog(Dialog):

    def __init__(self):
        super().__init__('class_dialog.ui')
        self.setWindowTitle('Class')

        self.table = menu.table_classes
        self.table_name = 'Classes'

        self.table_class_subjects.hideColumn(0)
        set_stretch(self.table_class_subjects)

    def show_info(self, row):

        super().show_info(row)
        con = sqlite3.connect(DATABASE_NAME)
        cur = con.cursor()

        tmp_subjects = cur.execute("SELECT id, title FROM Subjects").fetchall()
        current_class = cur.execute("SELECT * FROM Classes WHERE id = ?",
                                    (self.current_id,)).fetchone()
        con.close()

        if not isinstance(row, bool):
            self.cb_number.setCurrentIndex(
                int(self.table.item(row, 2).text()) - 1)

        self.table_class_subjects.setRowCount(0)
        for i in range(len(tmp_subjects)):

            self.table_class_subjects.setRowCount(
                self.table_class_subjects.rowCount() + 1)
            self.table_class_subjects.setItem(i, 0, QTableWidgetItem(
                str(tmp_subjects[i][0])))
            self.table_class_subjects.setItem(i, 1, QTableWidgetItem(
                str(tmp_subjects[i][1])))

            tmp_sb = QSpinBox(self)
            tmp_sb.setMaximum(20)
            self.table_class_subjects.setCellWidget(i, 2, tmp_sb)
            if current_class:

                if current_class[3].split()[::2].count(
                        str(tmp_subjects[i][0])) == 1:
                    index = current_class[3].split()[::2].index(
                        str(tmp_subjects[i][0]))

                    self.table_class_subjects.cellWidget(i, 2).setValue(
                        int(current_class[3].split()[1::2][index]))

        line_edit_interaction(self.le_name, self.table, row, 1)

        self.show()

    def get_values(self):

        if self.le_name.text() == '':
            raise IncorrectInputError('field name is empty')

        str_objects = ''
        for i in range(self.table_class_subjects.rowCount()):
            if self.table_class_subjects.cellWidget(i, 2).value() != 0:
                str_objects += self.table_class_subjects.item(i,
                                                              0).text() + ' '
                str_objects += str(
                    self.table_class_subjects.cellWidget(i, 2).value()) + ' '

        if str_objects == '':
            raise IncorrectInputError('no subjects')

        return [self.le_name.text(),
                self.cb_number.currentIndex() + 1,
                str_objects]


class TimetableView(Dialog):

    def __init__(self):
        super().__init__('timetable_view.ui')
        self.setWindowTitle('Timetable')
        set_stretch(self.table_all_days)

    def show_info(self, row):

        con = sqlite3.connect(DATABASE_NAME)
        cur = con.cursor()
        subjects = cur.execute("SELECT title FROM Subjects").fetchall()
        classes = cur.execute("SELECT name FROM Classes").fetchall()
        teachers = cur.execute(
            "SELECT surname, name, patronymic FROM Teachers").fetchall()
        con.close()

        for i in range(len(RESULT)):
            for k in range(len(RESULT[i])):
                if menu.tabWidget_2.currentIndex() == 1:

                    if len(RESULT[i][k]) == 1 and RESULT[i][k][0][1] == row:
                        self.table_all_days.setItem(i // 8, i % 8,
                                                    QTableWidgetItem(
                                                        str(classes[k][0])))
                        break
                    else:
                        self.table_all_days.setItem(i // 8, i % 8,
                                                    QTableWidgetItem(''))

                elif menu.tabWidget_2.currentIndex() == 0:
                    if len(RESULT[i][k]) == 1 and k == row:
                        subj = subjects[RESULT[i][k][0][0]][0] + ''
                        initials = str(teachers[RESULT[i][k][0][1]][0]) + ' '
                        initials += str(teachers[RESULT[i][k][0][1]][1])[
                                        0] + '. '
                        initials += str(teachers[RESULT[i][k][0][1]][2])[
                                        0] + '.'

                        self.table_all_days.setItem(i // 8, i % 8,
                                                    QTableWidgetItem(
                                                        str(subj + initials)))
                        break
                    else:
                        self.table_all_days.setItem(i // 8, i % 8,
                                                    QTableWidgetItem(''))

        if menu.tabWidget_2.currentIndex() == 1:

            self.label.setText('Timetable for ' + ' '.join(
                [str(i) for i in teachers[row][:3]]))

        elif menu.tabWidget_2.currentIndex() == 0:
            self.label.setText('Timetable for ' + str(classes[row][0]))
        self.statusBar().showMessage('')
        self.show()

    def save(self):

        document = Document()
        document.add_heading(self.label.text(), 0)
        table = document.add_table(rows=self.table_all_days.rowCount() + 1,
                                   cols=self.table_all_days.columnCount() + 1)
        week_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday',
                     'Saturday']

        for i in range(self.table_all_days.rowCount() + 1):
            cells = table.rows[i].cells
            for k in range(self.table_all_days.columnCount() + 1):
                if i != 0 and k != 0:
                    cells[k].text = self.table_all_days.item(i - 1,
                                                             k - 1).text()

                elif i == 0 and k != 0:
                    cells[k].text = str(k - 1)

                elif i != 0 and k == 0:
                    cells[k].text = week_days[i - 1]

        document.save(
            '_'.join(self.label.text().split()[2:]) + '_timetable.docx')
        self.statusBar().showMessage('Timetable save at ' + '_'.join(
            self.label.text().split()[2:]) + '_timetable.docx')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('icon.png'))

    menu = MainMenu()
    subject_dialog = SubjectDialog()
    teacher_dialog = TeacherDialog()
    class_dialog = ClassDialog()
    timetable_view = TimetableView()

    menu.show()
    sys.exit(app.exec())
