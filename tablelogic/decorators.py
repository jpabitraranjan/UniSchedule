from django.shortcuts import redirect

def student_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.session.get('user_type') != 'student':
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper

def teacher_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.session.get('user_type') != 'teacher':
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper
