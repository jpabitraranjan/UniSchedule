from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.exceptions import ValidationError
from django.db.models import Q

class Department(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Semester(models.Model):
    number = models.IntegerField()

    def __str__(self):
        return f"Semester {self.number}"

class Section(models.Model):
    name = models.CharField(max_length=10)
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)

    def __str__(self):
        return f"Sem {self.semester}, Dept {self.department}, Section {self.name}"

class Batch(models.Model):
    name = models.CharField(max_length=10)
    section = models.ForeignKey(Section, on_delete=models.CASCADE)

    def __str__(self):
        return f"Sem {self.section.semester.number}, Dept {self.section.department.name}, Section {self.section.name} - Batch {self.name}"

class Student(models.Model):
    usn = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    semester = models.IntegerField(choices=[(i, str(i)) for i in range(1, 9)])
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE)
    password = models.CharField(max_length=100, default = 'password')

    def __str__(self):
        return f"{self.usn} - {self.name}"

class Room(models.Model):
    name = models.CharField(max_length=20)

    def __str__(self):
        return self.name

class Teacher(models.Model):
    name = models.CharField(max_length=100)
    employee_id = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=100, default = 'password')


    def __str__(self):
        return self.name

class Course(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    lecture_hours = models.IntegerField(default=0)
    tutorial_hours = models.IntegerField(default=0)
    practical_hours = models.IntegerField(default=0)

    @property
    def total_credits(self):
        return self.lecture_hours + self.tutorial_hours // 2 + self.practical_hours // 2
    
    def __str__(self):
        return f"{self.code} - {self.name}"

# LECTURE assignment – applies to entire section
class LectureAssignment(models.Model):
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.course} - {self.teacher} (Section: {self.section})"


class TutorialAssignment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch, null=True, blank=True, on_delete=models.CASCADE)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    is_section_wide = models.BooleanField(default=False)

    def __str__(self):
        if self.is_section_wide:
            return f"{self.course.name} Tutorial (Section: {self.section.name}, Teacher: {self.teacher.name})"
        else:
            return f"{self.course.name} Tutorial (Batch: {self.batch.name}, Teacher: {self.teacher.name})"


class PracticalAssignment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch, null=True, blank=True, on_delete=models.CASCADE)
    teacher1 = models.ForeignKey(Teacher, related_name="practical_teacher1", on_delete=models.CASCADE)
    teacher2 = models.ForeignKey(Teacher, related_name="practical_teacher2", null=True, blank=True, on_delete=models.CASCADE)
    is_section_wide = models.BooleanField(default=False)

    def __str__(self):
        if self.is_section_wide:
            return f"{self.course.name} Practical (Section: {self.section.name}, Teachers: {self.teacher1.name} & {self.teacher2.name if self.teacher2 else 'N/A'})"
        else:
            return f"{self.course.name} Practical (Batch: {self.batch.name}, Teachers: {self.teacher1.name} & {self.teacher2.name if self.teacher2 else 'N/A'})"



class TimetableEntry(models.Model):
    DAY_CHOICES = [
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
    ]

    day = models.CharField(max_length=10, choices=DAY_CHOICES)
    period = models.IntegerField()
    room = models.ForeignKey(Room, on_delete=models.CASCADE)

    # Link to one of these
    lecture_assignment = models.ForeignKey(LectureAssignment, null=True, blank=True, on_delete=models.CASCADE)
    tutorial_assignment = models.ForeignKey(TutorialAssignment, null=True, blank=True, on_delete=models.CASCADE)
    practical_assignment = models.ForeignKey(PracticalAssignment, null=True, blank=True, on_delete=models.CASCADE)

    def clean(self):
        # Validate lecture assignments
        if self.lecture_assignment:
            course = self.lecture_assignment.course
            assignment = self.lecture_assignment
            entries = TimetableEntry.objects.filter(lecture_assignment=assignment)
            if self.pk is None:
                entries = entries.union(TimetableEntry.objects.none())
            if entries.count() + 1 > course.lecture_hours:
                raise ValidationError(
                    f"Cannot assign more than {course.lecture_hours} lecture periods for {course.name}."
                )

        # Validate tutorial assignments (must be in 2-hour blocks)
        if self.tutorial_assignment:
            course = self.tutorial_assignment.course
            assignment = self.tutorial_assignment
            tutorial_entries = TimetableEntry.objects.filter(tutorial_assignment=assignment)

            seen_blocks = set()
            for entry in tutorial_entries:
                block_start = entry.period if entry.period % 2 == 1 else entry.period - 1
                seen_blocks.add((entry.day, block_start))

            current_block_start = self.period if self.period % 2 == 1 else self.period - 1
            seen_blocks.add((self.day, current_block_start))

            if len(seen_blocks) > course.tutorial_hours // 2:
                raise ValidationError(
                    f"Cannot assign more than {course.tutorial_hours // 2} tutorial blocks (2 hrs each) for {course.name}."
                )

        # Validate practical assignments (must be in 2-hour blocks)
        if self.practical_assignment:
            course = self.practical_assignment.course
            assignment = self.practical_assignment
            practical_entries = TimetableEntry.objects.filter(practical_assignment=assignment)

            seen_blocks = set()
            for entry in practical_entries:
                block_start = entry.period if entry.period % 2 == 1 else entry.period - 1
                seen_blocks.add((entry.day, block_start))

            current_block_start = self.period if self.period % 2 == 1 else self.period - 1
            seen_blocks.add((self.day, current_block_start))

            if len(seen_blocks) > course.practical_hours // 2:
                raise ValidationError(
                    f"Cannot assign more than {course.practical_hours // 2} practical blocks (2 hrs each) for {course.name}."
                )

            # Automatically assign the next period for practicals (e.g., 5th period -> 6th period)
            if self.period % 2 == 1 and self.period < 6:
                next_period = self.period + 1
                # Check if the next period (6th) is already assigned
                next_period_entry = TimetableEntry.objects.filter(day=self.day, period=next_period).exists()
                if not next_period_entry:
                    # Create the next period's entry for practical
                    new_entry = TimetableEntry(
                        day=self.day,
                        period=next_period,
                        practical_assignment=self.practical_assignment,
                        room=self.room,
                    )
                    new_entry.save()  # Save the next period (6th)
                    # Optionally, validate the next period's time as well.

    def __str__(self):
        assignment = self.lecture_assignment or self.tutorial_assignment or self.practical_assignment
        return f"{self.day} Period {self.period} - {assignment.course.name} in {self.room.name}"


class ExtraClass(models.Model):
    date = models.DateField()
    period = models.IntegerField()
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, on_delete=models.CASCADE, null=True, blank=True)
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True)
    
    def __str__(self):
        return f"Extra class by {self.teacher.name} on {self.date} P{self.period} ({self.section.name if self.section else 'Section-Wide'}) in {self.room.name}"


class Message(models.Model):
    # Sender (student or teacher)
    sender_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='sent_messages')
    sender_object_id = models.PositiveIntegerField()
    sender = GenericForeignKey('sender_content_type', 'sender_object_id')

    # Receiver (student or teacher)
    receiver_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='received_messages')
    receiver_object_id = models.PositiveIntegerField()
    receiver = GenericForeignKey('receiver_content_type', 'receiver_object_id')

    # Message content
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender} ➡ {self.receiver}: {self.text[:30]}"
