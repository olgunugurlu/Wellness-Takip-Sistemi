# 🌿 Wellness Analiz Sistemi

Kullanıcı girişi, MySQL veritabanı ve Claude AI entegrasyonlu tam wellness analiz sistemi.

---

## Dosya Yapısı

```
wellness_app/
├── app.py                    ← Ana Streamlit uygulaması
├── db.py                     ← MySQL bağlantısı ve tablo oluşturma
├── auth.py                   ← Kayıt / giriş / oturum yönetimi
├── admin.py                  ← Admin paneli
├── claude_service.py         ← Claude API entegrasyonu
├── requirements.txt
├── .gitignore
└── .streamlit/
    └── secrets.toml          ← Bağlantı bilgileri (GitHub'a yükleme!)
```

---

## Kurulum

### 1. Paketleri yükleyin
```bash
pip install -r requirements.txt
```

### 2. secrets.toml dosyasını düzenleyin
`.streamlit/secrets.toml` dosyasını açın ve bilgilerinizi girin:
```toml
[mysql]
host     = "94.73.151.154"
database = "u1927296_olgundb"
user     = "kullanici_adiniz"
password = "parolaniz"
port     = 3306

[anthropic]
api_key  = "sk-ant-..."
```

### 3. Çalıştırın
```bash
streamlit run app.py
```

---

## Streamlit Cloud'a Deploy

1. `secrets.toml` dışındaki tüm dosyaları GitHub'a yükleyin
   (`secrets.toml` `.gitignore`'da zaten var, yüklenmez)

2. **share.streamlit.io** → "New app" → reponuzu seçin

3. "Advanced settings" → **Secrets** bölümüne `secrets.toml` içeriğini yapıştırın

4. Deploy edin

---

## İlk Admin Hesabı

Uygulama ilk çalıştığında tabloları otomatik oluşturur.
İlk kayıt olan kullanıcıyı admin yapmak için MySQL'de çalıştırın:

```sql
UPDATE wellness_users SET rol='admin' WHERE email='sizin@email.com';
```

---

## Veritabanı Tabloları

| Tablo | Açıklama |
|-------|----------|
| `wellness_users` | Kullanıcılar (id, ad, email, şifre, rol) |
| `wellness_forms` | Doldurulan formlar (JSON formatında) |
| `wellness_analyses` | Claude tarafından üretilen analizler |
