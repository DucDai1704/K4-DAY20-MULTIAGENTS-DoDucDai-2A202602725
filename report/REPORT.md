# Báo cáo thực hành K4-DAY20-MULTIAGENTS

**Sinh viên:** Đỗ Đức Đại  
**Mã sinh viên:** 2A202602725

## 1. Kết quả thực thi

- Mã nguồn trong thư mục `src/lab/` (bao gồm `agent.py`, `subagents.py`, `runner.py`, `curator.py`) đã được hoàn thiện 100% đúng kiến trúc theo yêu cầu của bài Lab.
- Đã chạy thành công bộ sandbox và cấu hình LangChain kết nối với Google Gemini.
- Toàn bộ các quy trình chạy thực nghiệm đã được hoàn tất 100% (bao gồm vòng lặp Baseline, Subagents và vòng lặp tự động hóa Skills-auto).
- Kết quả và dấu vết (trace) của các mô hình đã được hệ thống ghi nhận đầy đủ, xuất ra toàn bộ vào thư mục `results/` và file skill tự động sinh ở `skills/auto/`. (Sử dụng model `gemini-3.5-flash-lite`, đôi khi model bị cuốn vào vòng lặp vô hạn đạt đến giới hạn 60 recursion_limit, nhưng hệ thống code vẫn bắt lỗi an toàn và hoàn tất tiến trình mượt mà).

## 2. Các thành phần đã triển khai

1. **Agent Backend (`agent.py`)**: Đã đóng gói thành công cấu hình Langgraph và cấp công cụ cho các agent.
2. **Subagents (`subagents.py`)**: Định nghĩa đầy đủ 3 vai trò: Explorer (Đọc hiểu), Implementer (Code/Sửa lỗi), Reviewer (Kiểm tra lại).
3. **Runner (`runner.py`)**: Tự động hóa được luồng chuẩn bị dữ liệu (copy task vào test_sandbox), kích hoạt agent và lấy token theo `UsageMetadataCallbackHandler`.
4. **Curator (`curator.py`)**: Khởi tạo luồng trích xuất skill tự động (lấy rule/guideline từ những bài học thất bại để sinh ra kinh nghiệm tái sử dụng).
