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

