def has_time_conflict(course_to_add, student_courses):
    def parse_time(time_str):
        start, end = time_str.split('-')
        return tuple(map(lambda t: int(t.replace(':', '')), [start, end]))

    for enrolled_course in student_courses:
        for day1, time1 in enrolled_course['time_slots']:
            for day2, time2 in course_to_add['time_slots']:
                if day1 == day2:  # روز یکسان
                    start1, end1 = parse_time(time1)
                    start2, end2 = parse_time(time2)
                    # بررسی هم‌پوشانی
                    if start1 < end2 and start2 < end1:
                        return True
    return False




