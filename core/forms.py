from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings
import random
import string

from .models import Post, Comment


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')


class PasswordChangeForm(forms.Form):
    """密码修改表单 - 支持旧密码验证"""
    old_password = forms.CharField(
        label='旧密码',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'current-password'}),
    )
    new_password1 = forms.CharField(
        label='新密码',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),
    )
    new_password2 = forms.CharField(
        label='确认新密码',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_old_password(self):
        old_password = self.cleaned_data.get('old_password')
        if not self.user.check_password(old_password):
            raise forms.ValidationError('旧密码不正确')
        return old_password

    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('两次输入的密码不一致')
        return password2

    def save(self, commit=True):
        password = self.cleaned_data['new_password1']
        self.user.set_password(password)
        if commit:
            self.user.save()
        return self.user


class EmailVerificationForm(forms.Form):
    """邮箱验证表单 - 用于密码重置"""
    email = forms.EmailField(
        label='邮箱地址',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'autocomplete': 'email'}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email != self.user.email:
            raise forms.ValidationError('邮箱地址与当前用户邮箱不匹配')
        return email

    def send_verification_code(self):
        """生成并发送验证码"""
        code = ''.join(random.choices(string.digits, k=6))
        cache_key = f'password_reset_{self.user.pk}'
        cache.set(cache_key, code, timeout=300)  # 5分钟有效

        # 发送邮件
        subject = '密码重置验证码'
        message = f'您的验证码是：{code}，5分钟内有效。如非本人操作，请忽略此邮件。'
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@forum.local')

        try:
            send_mail(subject, message, from_email, [self.user.email])
            return True
        except Exception as e:
            # 开发环境：将验证码存入缓存供显示
            cache.set(f'password_reset_dev_{self.user.pk}', code, timeout=300)
            return False


class VerifyCodeForm(forms.Form):
    """验证码验证表单"""
    code = forms.CharField(
        label='验证码',
        max_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入6位验证码',
            'autocomplete': 'one-time-code',
        }),
    )
    new_password1 = forms.CharField(
        label='新密码',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),
    )
    new_password2 = forms.CharField(
        label='确认新密码',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_code(self):
        code = self.cleaned_data.get('code')
        cache_key = f'password_reset_{self.user.pk}'
        stored_code = cache.get(cache_key)
        if not stored_code:
            raise forms.ValidationError('验证码已过期，请重新获取')
        if code != stored_code:
            raise forms.ValidationError('验证码不正确')
        return code

    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('两次输入的密码不一致')
        return password2

    def save(self, commit=True):
        password = self.cleaned_data['new_password1']
        self.user.set_password(password)
        if commit:
            self.user.save()
            # 清除验证码
            cache.delete(f'password_reset_{self.user.pk}')
            cache.delete(f'password_reset_dev_{self.user.pk}')
        return self.user


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('title', 'content', 'category', 'tags', 'cover_image', 'is_published')
        widgets = {
            'tags': forms.CheckboxSelectMultiple,
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('content',)

