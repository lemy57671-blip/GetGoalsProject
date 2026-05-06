from pydantic import BaseModel, EmailStr

class SendMailRequest(BaseModel):
    to_email: EmailStr
    subject: str
    content: str