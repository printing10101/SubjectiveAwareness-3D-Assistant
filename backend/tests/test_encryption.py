from cryptography.fernet import Fernet

from app.utils.encryption import (
    EncryptedText,
    _get_cipher,
    _mask_bank_cards,
    _mask_emails,
    _mask_id_cards,
    _mask_phones,
    mask_sensitive_info,
)


class TestMaskSensitiveInfo:
    def test_mask_id_card(self):
        text = "身份证号：110101199001011234"
        result = mask_sensitive_info(text)
        assert "110101199001011234" not in result
        assert "110101" in result
        assert "1234" in result

    def test_mask_phone(self):
        text = "手机号：13812345678"
        result = mask_sensitive_info(text)
        assert "13812345678" not in result
        assert "138" in result
        assert "5678" in result
        assert "****" in result

    def test_mask_bank_card(self):
        text = "银行卡号：6222021234567890123"
        result = mask_sensitive_info(text)
        original = "6222021234567890123"
        assert original not in result
        assert "6222" in result
        assert "0123" in result

    def test_mask_email(self):
        text = "邮箱：zhangsan@example.com"
        result = mask_sensitive_info(text)
        assert "zhangsan" not in result
        assert "@example.com" in result
        assert "***@example.com" in result

    def test_mixed_sensitive_info(self):
        text = (
            "张三，身份证110101199001011234，电话13812345678，"
            "银行卡6222021234567890123，邮箱test@example.com"
        )
        result = mask_sensitive_info(text)
        assert "110101199001011234" not in result
        assert "13812345678" not in result
        assert "6222021234567890123" not in result
        assert "test@example.com" not in result
        assert "***@example.com" in result

    def test_no_sensitive_info(self):
        text = "这是一个普通的案件描述文本，不包含敏感信息。"
        result = mask_sensitive_info(text)
        assert result == text

    def test_empty_string(self):
        assert mask_sensitive_info("") == ""
        assert mask_sensitive_info(None) is None

    def test_multiple_id_cards(self):
        text = "身份证1：110101199001011234，身份证2：320106198805061234"
        result = mask_sensitive_info(text)
        assert "19900101" not in result
        assert "19880506" not in result

    def test_multiple_phones(self):
        text = "手机：13812345678 和 15987654321"
        result = mask_sensitive_info(text)
        assert "1234" not in result
        assert "8765" not in result

    def test_short_number_not_masked(self):
        text = "编号：12345"
        result = mask_sensitive_info(text)
        assert result == text


class TestPrivateMaskFunctions:
    def test_mask_id_cards_invalid(self):
        text = "数字12345678901234567890"
        result = _mask_id_cards(text)
        assert result == text

    def test_mask_phones_invalid_prefix(self):
        text = "电话：12345678901"
        result = _mask_phones(text)
        assert "12345678901" in result

    def test_mask_bank_cards_short(self):
        text = "卡号：1234567890"
        result = _mask_bank_cards(text)
        assert result == text

    def test_mask_emails_invalid(self):
        text = "没有邮箱地址"
        result = _mask_emails(text)
        assert result == text


class TestEncryptedText:
    def test_encrypt_decrypt(self):
        et = EncryptedText()
        original = "这是一段敏感的案件描述文本"
        encrypted = et.process_bind_param(original, None)
        assert encrypted != original
        decrypted = et.process_result_value(encrypted, None)
        assert decrypted == original

    def test_encrypt_none(self):
        et = EncryptedText()
        assert et.process_bind_param(None, None) is None
        assert et.process_result_value(None, None) is None

    def test_decrypt_invalid_data(self):
        """测试解密无效数据时返回 None."""
        et = EncryptedText()
        result = et.process_result_value("invalid_encrypted_data", None)
        # 解密失败时返回 None，而非原始字符串（安全考虑）
        assert result is None

    def test_encrypt_unicode(self):
        et = EncryptedText()
        original = "中文和法律术语：帮信罪、主观明知、帮助信息网络犯罪活动罪"
        encrypted = et.process_bind_param(original, None)
        decrypted = et.process_result_value(encrypted, None)
        assert decrypted == original

    def test_encrypt_long_text(self):
        et = EncryptedText()
        original = "a" * 10000
        encrypted = et.process_bind_param(original, None)
        decrypted = et.process_result_value(encrypted, None)
        assert decrypted == original

    def test_impl_is_text(self):
        assert EncryptedText.impl is not None


class TestGetCipher:
    def test_cipher_created_successfully(self):
        cipher = _get_cipher()
        assert isinstance(cipher, Fernet)

    def test_cipher_encrypt_decrypt(self):
        cipher = _get_cipher()
        original = b"test data for encryption"
        token = cipher.encrypt(original)
        decrypted = cipher.decrypt(token)
        assert decrypted == original
