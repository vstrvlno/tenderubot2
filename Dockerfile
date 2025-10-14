# ���������� ���������� Python 3.11.9
FROM python:3.11.9-slim

# ������������� ������� ����������
WORKDIR /app

# �������� � ������������� �����������
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# �������� ���� ������
COPY . .

# ��������� ���������� ��������� �� .env
# (Render ������������� ��������� ���� Environment Variables)
ENV PYTHONUNBUFFERED=1

# ������ ����
CMD ["python", "bot.py"]