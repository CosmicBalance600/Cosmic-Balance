FROM python:3.10-slim

# Çalışma klasörünü ayarla
WORKDIR /app

# Gerekli kütüphane dosyalarını kopyala
COPY requirements.txt .

# Kütüphaneleri kur
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodlarının tamamını kopyala
COPY . .

# Python konsolunun Docker içinde anında görünmesi için
ENV PYTHONUNBUFFERED=1
