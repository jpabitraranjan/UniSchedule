from django.shortcuts import render, get_object_or_404, redirect
from .models import *
from django.db import models
from django.http import HttpResponse
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from .decorators import student_required, teacher_required
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

class ExtraClassForm(forms.ModelForm):
    class Meta:
        model = ExtraClass
        fields = ['date', 'period', 'room']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        period = cleaned_data.get('period')
        room = cleaned_data.get('room')

        if not date or period is None or room is None:
            return cleaned_data

        weekday = date.strftime('%A')
        teacher = self.instance.teacher
        section = self.instance.section
        batch = self.instance.batch
        course = self.instance.course
        if ExtraClass.objects.filter(date=date, period=period, teacher=teacher).exists():
            raise ValidationError("Teacher already has an extra class at this time.")

        if ExtraClass.objects.filter(date=date, period=period, room=room).exists():
            raise ValidationError("Selected room is already occupied at this time.")

        if ExtraClass.objects.filter(date=date, period=period, section=section).exists():
            raise ValidationError("This section already has an extra class at this time.")

        if section:
            batches = section.batch_set.all()
            if ExtraClass.objects.filter(date=date, period=period, batch__in=batches).exists():
                raise ValidationError("A batch from this section already has an extra class at this time.")

        return cleaned_data

DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
PERIODS = [1, 2, 3, 4, 5, 6]

def home_view(request):
    return render(request, 'home.html')

def teacher_login_view(request):
    if request.method == 'POST':
        employee_id = request.POST['employee_id']
        password = request.POST['password']
        try:
            teacher = Teacher.objects.get(employee_id=employee_id, password=password)
            request.session['user_type'] = 'teacher'
            request.session['teacher_id'] = teacher.id
            return redirect('teacher_profile', teacher_id=teacher.id)
        except Teacher.DoesNotExist:
            return render(request, 'home.html', {'teacher_error': 'Invalid credentials'})
    return redirect('home')

def student_login_view(request):
    if request.method == 'POST':
        usn = request.POST['usn']
        password = request.POST['password']
        try:
            student = Student.objects.get(usn=usn, password=password)
            request.session['user_type'] = 'student'
            request.session['student_id'] = student.id
            return redirect('student_profile', student_id=student.id)
        except Student.DoesNotExist:
            return render(request, 'home.html', {'student_error': 'Invalid credentials'})
    return redirect('home')

def logout_view(request):
    request.session.flush()
    return redirect('home')

@student_required
def student_profile_view(request, student_id):
    if request.session['student_id'] != student_id:
        return redirect('home')
    student = get_object_or_404(Student, id=student_id)
    return render(request, 'student_profile.html', {'student': student})

@teacher_required
def teacher_profile_view(request, teacher_id):
    if request.session['teacher_id'] != teacher_id:
        return redirect('home')
    teacher = get_object_or_404(Teacher, id=teacher_id)
    teacher_lecture_assignments = LectureAssignment.objects.select_related('course').filter(teacher=teacher)
    teacher_tutorial_assignments = TutorialAssignment.objects.select_related('course').filter(teacher=teacher)
    teacher_practical_assignments = PracticalAssignment.objects.select_related('course').filter(
        Q(teacher1=teacher) | Q(teacher2=teacher)
    )

    return render(request, 'teacher_profile.html', {
        'teacher': teacher,
        'teacher_lecture_assignments': teacher_lecture_assignments,
        'teacher_tutorial_assignments': teacher_tutorial_assignments,
        'teacher_practical_assignments': teacher_practical_assignments,
    })

@student_required
def batch_timetable_view(request, batch_id):
    student = get_object_or_404(Student, id=request.session['student_id'])
    if student.batch.id != batch_id:
        return redirect('home')
    batch = get_object_or_404(Batch, id=batch_id)
    section = batch.section

    extra_classes = ExtraClass.objects.filter(
        models.Q(batch=batch) |
        (models.Q(batch__isnull=True) & models.Q(section=section))
    ).order_by('-date')

    timetable = {day: {period: None for period in PERIODS} for day in DAYS}

    entries = TimetableEntry.objects.filter(
        models.Q(lecture_assignment__section=section) |
        models.Q(tutorial_assignment__batch=batch) |
        models.Q(tutorial_assignment__section=section, tutorial_assignment__is_section_wide=True) |
        models.Q(practical_assignment__batch=batch) |
        models.Q(practical_assignment__section=section, practical_assignment__is_section_wide=True)
    ).distinct()

    for entry in entries:
        timetable[entry.day][entry.period] = entry

    timetable_data = []
    for day in DAYS:
        for period in PERIODS:
            timetable_data.append({
                'day': day,
                'period': period,
                'entry': timetable[day][period]
            })

    return render(request, 'batch_timetable.html', {
        'batch': batch,
        'timetable_data': timetable_data,
        'days': DAYS,
        'periods': PERIODS,
        'extra_classes': extra_classes,
    })

@teacher_required
def teacher_timetable_view(request, teacher_id):
    if request.session['teacher_id'] != teacher_id:
        return redirect('home')
    teacher = get_object_or_404(Teacher, pk=teacher_id)

    all_entries = TimetableEntry.objects.filter(
        Q(lecture_assignment__teacher=teacher) |
        Q(tutorial_assignment__teacher=teacher) |
        Q(practical_assignment__teacher1=teacher) |
        Q(practical_assignment__teacher2=teacher)
    ).distinct()

    entries = []
    for entry in all_entries:
        if entry.lecture_assignment:
            entries.append(entry)
        elif entry.tutorial_assignment:
            if entry.tutorial_assignment.is_section_wide or entry.tutorial_assignment.teacher == teacher:
                entries.append(entry)
        elif entry.practical_assignment:
            if entry.practical_assignment.is_section_wide or teacher in [entry.practical_assignment.teacher1, entry.practical_assignment.teacher2]:
                entries.append(entry)

    extra_classes = ExtraClass.objects.filter(teacher=teacher).order_by('-date')

    timetable_data = []
    for day in DAYS:
        for period in PERIODS:
            entry = next((e for e in entries if e.day == day and e.period == period), None)
            timetable_data.append({
                'day': day,
                'period': period,
                'entry': entry
            })

    context = {
        'teacher': teacher,
        'days': DAYS,
        'periods': PERIODS,
        'timetable_data': timetable_data,
        'extra_classes': extra_classes,
    }

    return render(request, 'teacher_timetable.html', context)


def get_available_slots_for_section(section, teacher):
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    periods = range(1, 7)
    available_slots = {day: {p: True for p in periods} for day in days}

    timetable_entries = TimetableEntry.objects.filter(
        Q(lecture_assignment__section=section) |
        Q(tutorial_assignment__section=section) |
        Q(practical_assignment__section=section)
    )

    teacher_entries = TimetableEntry.objects.filter(
        Q(lecture_assignment__teacher=teacher) |
        Q(tutorial_assignment__teacher=teacher) |
        Q(practical_assignment__teacher1=teacher) |
        Q(practical_assignment__teacher2=teacher)
    )

    for entry in timetable_entries.union(teacher_entries):
        available_slots[entry.day][entry.period] = False

    return available_slots


def get_available_slots_for_batch(batch, teacher):
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    periods = range(1, 7)
    available_slots = {day: {p: True for p in periods} for day in days}

    section = batch.section

    timetable_entries = TimetableEntry.objects.filter(
        Q(tutorial_assignment__batch=batch) |
        Q(practical_assignment__batch=batch) |
        Q(lecture_assignment__section=section) |
        Q(tutorial_assignment__section=section, tutorial_assignment__is_section_wide=True) |
        Q(practical_assignment__section=section, practical_assignment__is_section_wide=True)
    )

    teacher_entries = TimetableEntry.objects.filter(
        Q(lecture_assignment__teacher=teacher) |
        Q(tutorial_assignment__teacher=teacher) |
        Q(practical_assignment__teacher1=teacher) |
        Q(practical_assignment__teacher2=teacher)
    )

    for entry in timetable_entries.union(teacher_entries):
        available_slots[entry.day][entry.period] = False

    return available_slots

@teacher_required
def extra_class_for_section(request, section_id, teacher_id):
    if request.session['teacher_id'] != teacher_id:
        return redirect('home')

    section = get_object_or_404(Section, id=section_id)
    teacher = get_object_or_404(Teacher, id=teacher_id)
    available_slots = get_available_slots_for_section(section, teacher)
    
    extra_classes = ExtraClass.objects.filter(
        Q(section=section) | Q(batch__section=section) | Q(teacher=teacher)
    ).distinct().order_by('-date')

    if request.method == 'POST':
        instance = ExtraClass(teacher=teacher, section=section)
        form = ExtraClassForm(request.POST, instance=instance)

        if form.is_valid():
            extra_class = form.save(commit=False)
            weekday = extra_class.date.strftime('%A')

            if ExtraClass.objects.filter(date=extra_class.date, period=extra_class.period, teacher=teacher).exists():
                form.add_error(None, "Teacher already has an extra class at this time.")
            elif TimetableEntry.objects.filter(
                day=weekday,
                period=extra_class.period
            ).filter(
                Q(lecture_assignment__teacher=teacher) |
                Q(tutorial_assignment__teacher=teacher) |
                Q(practical_assignment__teacher1=teacher) |
                Q(practical_assignment__teacher2=teacher) |
                Q(lecture_assignment__section=section) |
                Q(tutorial_assignment__section=section) |
                Q(practical_assignment__section=section)
            ).exists():
                form.add_error(None, "There is a regular class scheduled at this time.")
            else:
                extra_class.save()
                return redirect('extra_class_for_section', section_id=section.id, teacher_id=teacher.id)
    else:
        form = ExtraClassForm()

    context = {
        'section': section,
        'teacher': teacher,
        'available_slots': available_slots,
        'extra_classes': extra_classes,
        'form': form,
        'days': DAYS,
        'periods': PERIODS,
    }
    return render(request, 'extra_class_for_section.html', context)


@teacher_required
def extra_class_for_batch(request, batch_id, teacher_id):
    if request.session['teacher_id'] != teacher_id:
        return redirect('home')

    batch = get_object_or_404(Batch, id=batch_id)
    section = batch.section
    teacher = get_object_or_404(Teacher, id=teacher_id)
    available_slots = get_available_slots_for_batch(batch, teacher)
    
    extra_classes = ExtraClass.objects.filter(
        Q(batch=batch) | Q(section=section) | Q(teacher=teacher)
    ).distinct().order_by('-date')

    if request.method == 'POST':
        instance = ExtraClass(teacher=teacher, section=section, batch=batch)
        form = ExtraClassForm(request.POST, instance=instance)

        if form.is_valid():
            extra_class = form.save(commit=False)
            weekday = extra_class.date.strftime('%A')

            if ExtraClass.objects.filter(date=extra_class.date, period=extra_class.period, teacher=teacher).exists():
                form.add_error(None, "Teacher already has an extra class at this time.")
            elif TimetableEntry.objects.filter(
                day=weekday,
                period=extra_class.period
            ).filter(
                Q(lecture_assignment__teacher=teacher) |
                Q(tutorial_assignment__teacher=teacher) |
                Q(practical_assignment__teacher1=teacher) |
                Q(practical_assignment__teacher2=teacher) |
                Q(lecture_assignment__section=section) |
                Q(tutorial_assignment__section=section) |
                Q(practical_assignment__section=section)
            ).exists():
                form.add_error(None, "There is a regular class scheduled at this time.")
            else:
                extra_class.save()
                return redirect('extra_class_for_batch', batch_id=batch.id, teacher_id=teacher.id)
    else:
        form = ExtraClassForm()

    context = {
        'batch': batch,
        'teacher': teacher,
        'available_slots': available_slots,
        'extra_classes': extra_classes,
        'form': form,
        'days': DAYS,
        'periods': PERIODS,
    }
    return render(request, 'extra_class_for_batch.html', context)


def chat_list_view(request, user_type, user_id):
    # Instead of trusting the user_id param, get from session
    if user_type == "student":
        current_user_id = request.session.get('student_id')
        if not current_user_id:
            return redirect('home')
        current_user = get_object_or_404(Student, id=current_user_id)
        students = Student.objects.exclude(id=current_user.id)  # Exclude self
        teachers = Teacher.objects.all()  # Show all teachers

    elif user_type == "teacher":
        current_user_id = request.session.get('teacher_id')
        if not current_user_id:
            return redirect('home')
        current_user = get_object_or_404(Teacher, id=current_user_id)
        students = Student.objects.all()  # Show all students
        teachers = Teacher.objects.exclude(id=current_user.id)  # Exclude self

    else:
        return redirect('home')

    context = {
        'user_type': user_type,
        'user_id': current_user.id,
        'user': current_user,
        'students': students,
        'teachers': teachers,
    }
    return render(request, 'chat_list.html', context)

def chat_room_view(request, user_type, user_id, receiver_type, receiver_id):
    # Identify sender (logged-in user)
    if user_type == "student":
        current_user = get_object_or_404(Student, id=request.session.get('student_id'))
    elif user_type == "teacher":
        current_user = get_object_or_404(Teacher, id=request.session.get('teacher_id'))
    else:
        return redirect('home')

    # Identify receiver
    if receiver_type == "student":
        receiver = get_object_or_404(Student, id=receiver_id)
    elif receiver_type == "teacher":
        receiver = get_object_or_404(Teacher, id=receiver_id)
    else:
        return redirect('home')

    # Get ContentTypes
    sender_ct = ContentType.objects.get_for_model(current_user)
    receiver_ct = ContentType.objects.get_for_model(receiver)

    # Filter messages for this chat only
    messages = Message.objects.filter(
        (
            Q(sender_content_type=sender_ct, sender_object_id=current_user.id,
             receiver_content_type=receiver_ct, receiver_object_id=receiver.id)
            |
            Q(sender_content_type=receiver_ct, sender_object_id=receiver.id,
             receiver_content_type=sender_ct, receiver_object_id=current_user.id)
        )
).order_by("timestamp")


    # Handle sending new message
    if request.method == "POST":
        text = request.POST.get("message")
        if text:
            Message.objects.create(
                sender_content_type=sender_ct,
                sender_object_id=current_user.id,
                receiver_content_type=receiver_ct,
                receiver_object_id=receiver.id,
                text=text
            )

            return redirect('chat_room', user_type=user_type, user_id=user_id,
                            receiver_type=receiver_type, receiver_id=receiver_id)

    return render(request, 'chat_room.html', {
        'user': current_user,
        'receiver': receiver,
        'messages': messages,
        'user_type': user_type,
        'user_id': user_id,
    })