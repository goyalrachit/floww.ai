import subprocess
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
import json
import uuid
from .services import mermaid_generator
from .models import ChatSession, ChatMessage, DiagramHistory


def home_view(request):
    """Landing page - accessible to all users"""
    if request.user.is_authenticated:
        # If user is already logged in, redirect to chat interface
        return redirect('diagram_app:chat_interface')
    return render(request, "diagram_app/home.html")


# Authentication Views
def signup_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        # Validation
        if password != confirm_password:
            messages.error(request, 'Passwords do not match')
            return render(request, 'registration/signup.html')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return render(request, 'registration/signup.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists')
            return render(request, 'registration/signup.html')
        
        # Create user
        user = User.objects.create_user(username=username, email=email, password=password)
        login(request, user)
        messages.success(request, 'Account created successfully!')
        return redirect('diagram_app:chat_interface')
    
    return render(request, 'registration/signup.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'diagram_app:chat_interface')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'registration/login.html')

def logout_view(request):
    logout(request)
    return redirect('diagram_app:home')  # Redirect to home instead of login

# Chat Views with Authentication
@login_required
def chat_interface(request, session_id=None):
    """Main chat interface with sidebar preview"""
    if session_id:
        try:
            chat_session = get_object_or_404(ChatSession, session_id=session_id, user=request.user)
        except:
            chat_session = ChatSession.objects.create(user=request.user)
            return redirect('diagram_app:chat_interface_with_session', session_id=chat_session.session_id)
    else:
        # Create new session if none specified
        chat_session = ChatSession.objects.create(user=request.user)
        return redirect('diagram_app:chat_interface_with_session', session_id=chat_session.session_id)
    
    # Update session in Django session
    request.session['chat_session_id'] = str(chat_session.session_id)
    
    # Get chat history for current session
    chat_history = ChatMessage.objects.filter(session=chat_session).order_by('timestamp')
    
    # Get all user's chat sessions for sidebar (limit to recent 20)
    chat_sessions = ChatSession.objects.filter(user=request.user)[:20]
    
    return render(request, 'diagram_app/chat_interface.html', {
        'session_id': str(chat_session.session_id),
        'chat_history': chat_history,
        'chat_sessions': chat_sessions,
        'current_session': chat_session,
    })

@login_required
def new_session_view(request):
    """Create a new chat session and redirect to it"""
    chat_session = ChatSession.objects.create(user=request.user)
    return redirect('diagram_app:chat_interface_with_session', session_id=chat_session.session_id)

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def delete_session(request, session_id):
    """Delete a chat session"""
    try:
        session = get_object_or_404(ChatSession, session_id=session_id, user=request.user)
        session.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def send_message(request):
    """Handle chat messages with context awareness"""
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id')
        
        if not user_message:
            return JsonResponse({'error': 'Message cannot be empty'}, status=400)
        
        # Get the session and verify ownership
        session = get_object_or_404(ChatSession, session_id=session_id, user=request.user)
        
        # Update title if it's the first message
        if not session.title and session.messages.count() == 0:
            title = user_message[:50] + "..." if len(user_message) > 50 else user_message
            session.title = title
            session.save()
        
        # Generate contextual response
        result = mermaid_generator.generate_response_with_context(session_id, user_message)
        
        if 'error' in result:
            return JsonResponse({'error': result['error']}, status=500)
        
        # Save diagram if Mermaid code was generated
        if result.get('mermaid_code'):
            DiagramHistory.objects.create(
                session=session,
                user_prompt=user_message,
                mermaid_code=result['mermaid_code']
            )
        
        return JsonResponse({
            'success': True,
            'response': result['response'],
            'mermaid_code': result.get('mermaid_code'),
            'session_id': result['session_id']
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# Your other existing views remain the same but add @login_required where needed
@login_required
@require_http_methods(["GET"])
def get_chat_history(request, session_id):
    """Get chat history for a session"""
    try:
        session = get_object_or_404(ChatSession, session_id=session_id, user=request.user)
        messages = ChatMessage.objects.filter(session=session).order_by('timestamp')
        
        history = []
        for msg in messages:
            history.append({
                'type': msg.message_type,
                'content': msg.content,
                'mermaid_code': msg.mermaid_code,
                'timestamp': msg.timestamp.isoformat()
            })
        
        return JsonResponse({'history': history})
        
    except ChatSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)

@login_required
@csrf_exempt
def new_session(request):
    """API endpoint for creating new session"""
    chat_session = ChatSession.objects.create(user=request.user)
    session_id = str(chat_session.session_id)
    request.session['chat_session_id'] = session_id
    return JsonResponse({'session_id': session_id})

@login_required
def simple_editor(request):
    """Simple fullscreen editor"""
    return render(request, 'diagram_app/fullscreen_editor.html')

# Keep your existing export_diagram and save_diagram_edit views

@require_http_methods(["POST"])
def export_diagram(request):
    try:
        data = json.loads(request.body)
        mermaid_code = data.get('mermaid_code')
        format = data.get('format', 'svg')
        if format not in ['svg', 'png']:
            return JsonResponse({'error': 'Unsupported format'}, status=400)
        process = subprocess.run(
            ['mmdc', '-i', '-', '-o', '-', f'--{format}'],
            input=mermaid_code.encode(),
            capture_output=True
        )
        if process.returncode != 0:
            return JsonResponse({'error': 'Failed to generate diagram'}, status=500)
        content_type = 'image/svg+xml' if format == 'svg' else 'image/png'
        response = HttpResponse(content=process.stdout, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename=diagram.{format}'
        return response
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def save_diagram_edit(request):
    """Save edited diagram"""
    try:
        data = json.loads(request.body)
        diagram_id = data.get('diagram_id')
        mermaid_code = data.get('mermaid_code')
        title = data.get('title', 'Untitled Diagram')
        
        if diagram_id:
            # Update existing diagram
            diagram = DiagramHistory.objects.get(id=diagram_id)
            diagram.mermaid_code = mermaid_code
            diagram.save()
        else:
            # Create new diagram
            diagram = DiagramHistory.objects.create(
                user_prompt=title,
                mermaid_code=mermaid_code
            )
        
        return JsonResponse({
            'success': True,
            'diagram_id': diagram.id,
            'message': 'Diagram saved successfully'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)