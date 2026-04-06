# LMS System

A Django-based Learning Management System built with server-rendered templates, role-based access, course management, chapter content, quizzes, articles, and enrollment workflows.

## Stack

- Django 5.2
- MySQL
- Bootstrap UI
- Custom user model

## Core Modules

- Authentication with custom `User` model
- Roles: Admin, Teacher, Student
- Email OTP verification for teacher and student registration
- Admin approval and block/unblock flow
- Profile management with optional avatar upload
- Courses and enrollments
- Chapters with formatted content editor and chapter reader
- One quiz per chapter with teacher-side quiz management
- Student quiz attempts with saved results and one-attempt protection
- Article writing competition with approval and winner selection

## Project Structure

- `users/` - authentication, roles, dashboards, profile, admin user management
- `courses/` - courses, chapters, enrollments
- `quizzes/` - chapter quizzes, questions, answers, attempts, results
- `articles/` - writing competition module
- `templates/` - shared project templates
- `static/` - static assets
- `media/` - uploaded files such as profile images

## Requirements

Install dependencies:

```bash
pip install -r requirements.txt
```

Current dependencies are pinned in [requirements.txt](/var/www/html/lms_system/requirements.txt).

## Environment Variables

Create a `.env` file in the project root with values similar to:

```env
SECRET_KEY=your_generated_secret_key

DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_HOST=127.0.0.1
DB_PORT=3306

EMAIL_HOST=
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
DEFAULT_FROM_EMAIL=
EMAIL_OTP_EXPIRY_MINUTES=10
```

Notes:

- `SECRET_KEY` is required
- if SMTP settings are omitted, the project falls back to Django's console email backend locally
- `ALLOWED_HOSTS` is currently managed in settings files

## Setup

1. Create and activate a virtual environment.
2. Install dependencies.
3. Configure `.env`.
4. Create a MySQL database.
5. Run migrations.
6. Create a superuser.
7. Start the development server.

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Authentication Flow

- Unauthenticated users are redirected to the login page
- Teacher and student registration requires:
  - first name
  - last name
  - username
  - email
  - role
  - phone number
  - optional address
  - optional profile image
- Teacher and student accounts verify email through OTP
- Admin must approve teacher and student accounts before full access

## Role Access

- Admin
  - dashboard overview
  - manage teachers and students
  - approve, block, delete users
  - mark winning article
- Teacher
  - create and manage courses
  - create and manage chapters
  - create and manage chapter quizzes
  - view enrollments and student lists
  - review article submissions
- Student
  - enroll in courses
  - read chapters
  - attempt quizzes
  - submit articles

## Quiz Attempt System

- Each chapter can have one quiz
- Students can attempt a chapter quiz once
- Every answer submission is saved
- Score is calculated and stored in `QuizAttempt`
- Result page shows:
  - score
  - submitted answers
  - correct answers

## Media and Static Files

- Static files are served from `static/`
- Uploaded media is stored in `media/`
- Add the authentication background image at:

```text
static/images/auth-bg.jpg
```

## Helpful Commands

```bash
python manage.py check
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

## Important Notes

- If you switch to a custom user model after initial migrations, reset or carefully rebuild the database migration history
- Image uploads require `Pillow`
- MySQL access must be available for full migration and runtime testing

