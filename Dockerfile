FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

#첫번째 점: 내 컴퓨터의 현재 폴더의 모든 것, 두번째 점: 컨테이너의 현재 작업 디렉토리
COPY . . 

#정적파일 관련
RUN python manage.py collectstatic --no-input

#config 이름 주의
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "careon.asgi:application"]