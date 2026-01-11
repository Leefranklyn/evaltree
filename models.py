from mongoengine import Document, fields, connect
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import uuid

class User(Document):
    email = fields.EmailField(unique=True)
    name = fields.StringField()
    hashed_password = fields.StringField()
    role = fields.StringField(choices=["admin", "student"])
    school_id = fields.StringField(required=False)

class QuestionEmbedded(fields.EmbeddedDocument):
    text = fields.StringField()
    options = fields.ListField(fields.StringField())
    correct_option = fields.IntField()

class Quiz(Document):
    title = fields.StringField()
    duration_minutes = fields.IntField()
    questions = fields.EmbeddedDocumentListField(QuestionEmbedded)
    code = fields.StringField(unique=True)
    creator_email = fields.EmailField()
    total_points = fields.IntField(min_value=1, default=100)

class Submission(Document):
    student_email = fields.EmailField()
    quiz_id = fields.ObjectIdField()
    answers = fields.ListField(fields.IntField())
    score = fields.IntField()
    submitted_at = fields.DateTimeField()

class UserBase(BaseModel):
    email: EmailStr
    name: str
    password: str

class StudentCreate(UserBase):
    school_id: str

class AdminCreate(UserBase):
    secret_code: str 

class Token(BaseModel):
    access_token: str
    token_type: str

class Question(BaseModel):
    text: str
    options: List[str]
    correct_option: int

class QuizCreate(BaseModel):
    title: str
    duration_minutes: int

class SubmissionCreate(BaseModel):
    answers: List[int]