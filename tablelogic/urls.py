from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('teacher/login/', views.teacher_login_view, name='teacher_login'),
    path('student/login/', views.student_login_view, name='student_login'),
    path('student/<int:student_id>/', views.student_profile_view, name='student_profile'),
    path('batch/<int:batch_id>/', views.batch_timetable_view, name='batch_timetable'),
    path('teacher/<int:teacher_id>/timetable', views.teacher_timetable_view, name='teacher_timetable'),
    path('teacher/<int:teacher_id>/', views.teacher_profile_view, name='teacher_profile'),
    path('teacher/<int:teacher_id>/extra-class/batch/<int:batch_id>/', views.extra_class_for_batch, name='extra_class_for_batch'),
    path('teacher/<int:teacher_id>/extra-class/section/<int:section_id>/', views.extra_class_for_section, name='extra_class_for_section'),
    path('<str:user_type>/<int:user_id>/chat/', views.chat_list_view, name='chat_list'),
    path('<str:user_type>/<int:user_id>/chat/<str:receiver_type>/<int:receiver_id>/', views.chat_room_view, name='chat_room'),
]