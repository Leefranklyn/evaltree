from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from models import AdminCreate, QuizCreate, QuestionEmbedded, Quiz, Submission, User
from auth import get_password_hash, create_access_token, get_current_user, verify_password
from fastapi.templating import Jinja2Templates
import uuid
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

router = APIRouter()
templates = Jinja2Templates(directory="templates")

ADMIN_SECRET = os.getenv("ADMIN_SECRET")

@router.get("/signup", response_class=HTMLResponse)
async def admin_signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request, "role": "admin"})

@router.post("/signup")
async def admin_signup(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    secret_code: str = Form(...)
):
    if secret_code != str(ADMIN_SECRET):
        raise HTTPException(status_code=400, detail="Invalid secret code")
    if User.objects(email=email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(password)
    user = User(name=name, email=email, hashed_password=hashed_password, role="admin")
    user.save()
    return RedirectResponse(url="/admin/login", status_code=303)

@router.get("/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "role": "admin"})

@router.post("/login")
async def admin_login(email: str = Form(...), password: str = Form(...)):
    user = User.objects(email=email, role="admin").first()
    print(user,id)
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    access_token = create_access_token(user.email)

    response = RedirectResponse(
        url="/admin/dashboard",
        status_code=303 
    )
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,          
        secure=False,          
        samesite="lax"
    )
    
    return response

@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    # Get all quizzes created by this admin
    quizzes = Quiz.objects(creator_email=current_user.email).order_by("-id")

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": current_user,
            "quizzes": quizzes
        }
    )
    
@router.get("/quiz_details/{quiz_id}", response_class=HTMLResponse)
async def quiz_details(
    quiz_id: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    quiz = Quiz.objects(id=quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    if quiz.creator_email != current_user.email:
        raise HTTPException(status_code=403, detail="You don't own this quiz")

    # Get all submissions
    submissions = Submission.objects(quiz_id=quiz.id).order_by("-submitted_at")

    # Enrich each submission with student info
    enriched_submissions = []
    total_questions = len(quiz.questions)
    total_points = quiz.total_points
    for sub in submissions:
        student = User.objects(email=sub.student_email).first()
        correct_count = sub.score
        
        points_earned = 0
        if total_questions > 0:
            points_earned = round((correct_count / total_questions) * quiz.total_points)
            
        enriched_submissions.append({
            "name": student.name if student else "Unknown",
            "school_id": student.school_id if student else "N/A",
            "email": sub.student_email,
            "correct_count": sub.score,
            "total_questions": len(quiz.questions),
            "points_earned": points_earned,
            "total_points": total_points,
            "submitted_at": sub.submitted_at.strftime('%Y-%m-%d %H:%M')
        })

    total_students = len(enriched_submissions)
    avg_correct = sum(s["correct_count"] for s in enriched_submissions) / total_students if total_students > 0 else 0
    avg_points = sum(s["points_earned"] for s in enriched_submissions) / total_students if total_students > 0 else 0

    return templates.TemplateResponse(
        "quiz_details.html",
        {
            "request": request,
            "quiz": quiz,
            "submissions": enriched_submissions,
            "total_students": total_students,
            "avg_correct": round(avg_correct, 1),
            "avg_points": round(avg_points, 1),
            "total_questions": total_questions,
            "total_points": quiz.total_points
        }
    )

@router.get("/create_quiz", response_class=HTMLResponse)
async def create_quiz_page(request: Request, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    return templates.TemplateResponse("create_quiz.html", {"request": request})

@router.post("/create_quiz")
async def create_quiz(
    title: str = Form(...),
    duration_minutes: int = Form(...),
    total_points: int = Form(100),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    if duration_minutes <= 0:
        raise HTTPException(status_code=400, detail="Duration must be positive")
    code = str(uuid.uuid4())[:8].upper()
    quiz = Quiz(title=title, duration_minutes=duration_minutes, total_points=total_points, code=code, creator_email=current_user.email)
    quiz.save()
    return RedirectResponse(url=f"/admin/add_questions/{quiz.id}", status_code=303)

@router.get("/add_questions/{quiz_id}", response_class=HTMLResponse)
async def add_questions_page(quiz_id: str, request: Request, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    quiz = Quiz.objects(id=quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return templates.TemplateResponse("add_question.html", {"request": request, "quiz_id": quiz_id, "questions": quiz.questions})

@router.post("/add_questions/{quiz_id}")
async def add_question(
    quiz_id: str,
    text: str = Form(...),
    options: list[str] = Form(...),
    correct_option: int = Form(...),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    quiz = Quiz.objects(id=quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    if len(options) < 2 or correct_option < 0 or correct_option >= len(options):
        raise HTTPException(400, "Invalid options or correct index")
    question = QuestionEmbedded(text=text, options=options, correct_option=correct_option)
    quiz.questions.append(question)
    quiz.save()
    return RedirectResponse(url=f"/admin/add_questions/{quiz_id}", status_code=303)

@router.post("/edit_question/{quiz_id}/{index}")
async def edit_question(
    quiz_id: str,
    index: int,
    text: str = Form(...),
    options: list[str] = Form(...),
    correct_option: int = Form(...),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403)

    quiz = Quiz.objects(id=quiz_id).first()
    if not quiz or index >= len(quiz.questions):
        raise HTTPException(status_code=404)

    quiz.questions[index].text = text
    quiz.questions[index].options = options
    quiz.questions[index].correct_option = correct_option
    quiz.save()

    return RedirectResponse(
        url=f"/admin/add_questions/{quiz_id}",
        status_code=303
    )

@router.post("/delete_question/{quiz_id}/{index}")
async def delete_question(
    quiz_id: str,
    index: int,
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403)

    quiz = Quiz.objects(id=quiz_id).first()
    if not quiz or index >= len(quiz.questions):
        raise HTTPException(status_code=404)

    quiz.questions.pop(index)
    quiz.save()

    return RedirectResponse(
        url=f"/admin/add_questions/{quiz_id}",
        status_code=303
    )

@router.post("/finish_quiz/{quiz_id}")
async def finish_quiz(quiz_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    quiz = Quiz.objects(id=quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return RedirectResponse(url=f"/admin/quiz_code/{quiz_id}", status_code=303)

@router.get("/quiz_code/{quiz_id}", response_class=HTMLResponse)
async def show_quiz_code(quiz_id: str, request: Request, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    quiz = Quiz.objects(id=quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return templates.TemplateResponse("quiz_code.html", {"request": request, "code": quiz.code})

@router.get("/logout", response_class=HTMLResponse)
async def admin_logout():
    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie(key="access_token")
    return response