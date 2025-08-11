## Contract Processing Pipeline (Hotels) - Docling + LLM

### Yêu cầu môi trường

- Python 3.11+
- Tạo file `.env` ở thư mục gốc với nội dung:

```
DOCLING_API_URL=http://172.17.0.1:5001/v1/convert/file
OPENAI_API_KEY=sk-...
DATA_DIR=/home/ebk/AI.ROVI/Contract Test/data
```

### Cài đặt & chạy

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Endpoints chính

- POST `/contracts/base/ingest` (multipart file PDF)
- POST `/contracts/{id}/addenda/ingest` (multipart file PDF)
- GET `/contracts/{id}/state?as_of=YYYY-MM-DD`
- GET `/contracts/{id}/versions/{v}/redline`

### Ghi chú
- Hệ thống sẽ gọi Docling tại `DOCLING_API_URL` kèm form-data params OCR/table như mô tả.
- LLM yêu cầu `OPENAI_API_KEY`; response dạng JSON theo schema.
- Kết quả version JSON và render MD lưu ở `DATA_DIR`. 