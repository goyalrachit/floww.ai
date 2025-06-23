from django.urls import path
from . import views

app_name = 'diagram_app'

urlpatterns = [
    # Authentication URLs
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Main chat interface
    path('chat_interface/', views.chat_interface, name='chat_interface'),
    path('', views.home_view, name='home'),
    path('chat/<uuid:session_id>/', views.chat_interface, name='chat_interface_with_session'),
    
    # Session management
    path('new-chat/', views.new_session_view, name='new_session_view'),
    path('delete-session/<uuid:session_id>/', views.delete_session, name='delete_session'),
    
    # Chat functionality
    path('send-message/', views.send_message, name='send_message'),
    path('chat-history/<str:session_id>/', views.get_chat_history, name='chat_history'),
    path('new-session/', views.new_session, name='new_session'),
    
    # Existing functionality
    path('export-diagram/', views.export_diagram, name='export_diagram'),
    path('simple-editor/', views.simple_editor, name='simple_editor'),
    path('save-edit/', views.save_diagram_edit, name='save_diagram_edit'),
]
