from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.params import Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from models import StudentCreate, Quiz, Submission, SubmissionCreate, User
from auth import get_password_hash, create_access_token, get_current_user, verify_password
from fastapi.templating import Jinja2Templates
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/signup", response_class=HTMLResponse)
async def student_signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request, "role": "student"})

@router.post("/signup")
async def student_signup(
    school_id: str = Form(...),
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...)
):
    if User.objects(email=email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(password)
    user = User(school_id=school_id, name=name, email=email, hashed_password=hashed_password, role="student")
    user.save()
    return RedirectResponse(url="/student/login", status_code=303)

@router.get("/login", response_class=HTMLResponse)
async def student_login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "role": "student"})

@router.post("/login")
async def student_login(email: str = Form(...), password: str = Form(...)):
    user = User.objects(email=email, role="student").first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    access_token = create_access_token(user.email)
    response = RedirectResponse(url="/student/enter_code", status_code=303)
    response.set_cookie(key="access_token", value=access_token)
    return response

@router.get("/enter_code", response_class=HTMLResponse)
async def enter_code_page(request: Request, current_user: User = Depends(get_current_user)):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Not authorized")
    return templates.TemplateResponse("enter_code.html", {"request": request})

@router.post("/enter_code")
async def enter_code(
    request: Request,
    code: str = Form(...),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Not authorized")

    quiz = Quiz.objects(code=code).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Invalid quiz code")

    already_taken = Submission.objects(
        student_email=current_user.email,
        quiz_id=quiz.id
    ).first() is not None

    if already_taken:
        return templates.TemplateResponse(
            "enter_code.html",
            {
                "request": request,
                "error_message": f"You have already taken this quiz.",
                "show_alert": True
            }
        )

    return RedirectResponse(
        url=f"/student/take_quiz/{quiz.id}",
        status_code=303
    )

@router.get("/take_quiz/{quiz_id}", response_class=HTMLResponse)
async def take_quiz_page(quiz_id: str, request: Request, current_user: User = Depends(get_current_user)):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    quiz = Quiz.objects(id=quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # Prepare data with indices
    quiz_dict = quiz.to_mongo().to_dict()
    for q in quiz_dict['questions']:
        q['numbered_options'] = list(enumerate(q['options']))
    
    already_submitted = Submission.objects(
        student_email=current_user.email,
        quiz_id=quiz.id
    ).first() is not None

    if already_submitted:
        return RedirectResponse(
            url=f"/student/already_taken?quiz_title={quiz.title}",
            status_code=303
        )
        
    return templates.TemplateResponse(
        "take_quiz.html",
        {"request": request, "quiz": quiz_dict, "duration": quiz.duration_minutes}
    )
    
@router.get("/already_taken", response_class=HTMLResponse)
def already_taken_page(
    request: Request,
    quiz_title: str = Query("this quiz"),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Not authorized")

    return templates.TemplateResponse(
        "already_taken.html",
        {"request": request, "quiz_title": quiz_title}
    )

@router.post("/submit_quiz/{quiz_id}")
async def submit_quiz(quiz_id: str, request: Request, current_user: User = Depends(get_current_user)):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Not authorized")

    quiz = Quiz.objects(id=quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    form = await request.form()
    answers = []
    for i in range(len(quiz.questions)):
        ans_key = f"q{i+1}"
        try:
            answers.append(int(form.get(ans_key, -1)))
        except ValueError:
            answers.append(-1)

    score = 0
    for idx, q in enumerate(quiz.questions):
        if idx < len(answers) and answers[idx] == q.correct_option:
            score += 1
    
    # Save the submission
    submission = Submission(
        student_email=current_user.email,
        quiz_id=quiz.id,
        answers=answers,
        score=score,
        submitted_at=datetime.utcnow()
    )
    submission.save()

    return RedirectResponse(
        url="/student/thank_you",
        status_code=303
    )
    
@router.get("/thank_you", response_class=HTMLResponse)
async def thank_you_page(request: Request, current_user: User = Depends(get_current_user)):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return templates.TemplateResponse(
        "thank_you.html",
        {"request": request}
)

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie("access_token")
    return response