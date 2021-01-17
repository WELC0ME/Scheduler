from dialog import Dialog


class TimetablDialog(Dialog):

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
