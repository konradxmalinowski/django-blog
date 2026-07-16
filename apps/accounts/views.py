import base64
import io
import logging
import pyotp
import qrcode

from django.conf import settings as django_settings
from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.core.mail import BadHeaderError
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils.http import url_has_allowed_host_and_scheme
from django_ratelimit.decorators import ratelimit

logger = logging.getLogger(__name__)

from apps.accounts.forms import ChangeEmailForm, RegisterForm, TOTPVerifyForm, UserProfileForm
from apps.accounts.models import EmailVerificationToken, TwoFactorBackupCode, UserProfile
from apps.accounts.utils import log_action
from apps.blog.models import Post


def _send_verification_email(request, user, token):
    subject = render_to_string('email/verify_email_subject.txt').strip()
    verify_url = request.build_absolute_uri(
        f'/accounts/verify-email/{token.token}/'
    )
    body = render_to_string('email/verify_email.txt', {
        'user': user,
        'verify_url': verify_url,
    })
    send_mail(subject, body, None, [user.email])


@ratelimit(key='ip', rate='10/h', method='POST', block=True)
def register(request):
    if request.user.is_authenticated:
        return redirect('blog:post_list')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            if getattr(django_settings, 'DEMO_MODE', False):
                user.is_active = True
                user.save()
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                log_action(request, user, 'register')
                messages.info(request, 'Tryb demo - konto aktywowane automatycznie (bez weryfikacji email).')
                return redirect('blog:post_list')
            user.is_active = False
            user.save()
            token = EmailVerificationToken.objects.create(user=user)
            try:
                _send_verification_email(request, user, token)
            except (BadHeaderError, OSError, Exception) as exc:
                logger.error('Registration email failed for %s: %s', user.email, exc)
                user.delete()
                messages.error(
                    request,
                    'Nie udało się wysłać e-maila weryfikacyjnego. '
                    'Sprawdź konfigurację serwera pocztowego lub spróbuj ponownie później.',
                )
                return render(request, 'accounts/register.html', {'form': form})
            log_action(request, user, 'register')
            return redirect('accounts:verify_email_sent')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


def verify_email_sent(request):
    return render(request, 'accounts/verify_email_sent.html')


def verify_email(request, token):
    try:
        verification = EmailVerificationToken.objects.select_related('user').get(token=token)
    except EmailVerificationToken.DoesNotExist:
        messages.error(request, 'Link weryfikacyjny jest nieprawidłowy.')
        return redirect('accounts:login')

    if not verification.is_valid():
        messages.error(request, 'Link weryfikacyjny wygasł lub został już użyty.')
        return redirect('accounts:login')

    user = verification.user
    user.is_active = True
    user.save()
    verification.used = True
    verification.save()

    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    messages.success(request, 'Adres e-mail został potwierdzony. Witaj w DevLog!')
    return redirect('accounts:profile')


@login_required
def profile(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    posts = Post.published.filter(author=request.user).order_by('-publish')
    return render(request, 'accounts/profile.html', {
        'profile': profile,
        'posts': posts,
    })


@login_required
def edit_profile(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=profile)
    return render(request, 'accounts/edit_profile.html', {'form': form})


def public_profile(request, username):
    user = get_object_or_404(User, username=username)
    profile, _ = UserProfile.objects.get_or_create(user=user)
    posts = Post.published.filter(author=user).order_by('-publish')
    return render(request, 'accounts/public_profile.html', {
        'profile_user': user,
        'profile': profile,
        'posts': posts,
    })


@login_required
def account_settings(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    return render(request, 'accounts/settings.html', {'profile': profile})


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            log_action(request, request.user, 'password_change')
            messages.success(request, 'Hasło zostało zmienione.')
            return redirect('accounts:settings')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'accounts/change_password.html', {'form': form})


@login_required
def change_email(request):
    if request.method == 'POST':
        form = ChangeEmailForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            log_action(request, request.user, 'email_change')
            messages.success(request, 'Adres e-mail został zmieniony.')
            return redirect('accounts:settings')
    else:
        form = ChangeEmailForm(request.user)
    return render(request, 'accounts/change_email.html', {'form': form})


@login_required
def setup_2fa(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if profile.two_factor_enabled:
        return redirect('accounts:settings')

    if not profile.totp_secret:
        profile.totp_secret = pyotp.random_base32()
        profile.save()

    totp = pyotp.TOTP(profile.totp_secret)
    otp_uri = totp.provisioning_uri(
        name=request.user.email or request.user.username,
        issuer_name='DevLog',
    )

    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(otp_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    qr_b64 = base64.b64encode(buf.getvalue()).decode()

    if request.method == 'POST':
        form = TOTPVerifyForm(request.POST)
        if form.is_valid():
            if totp.verify(form.cleaned_data['code']):
                profile.two_factor_enabled = True
                profile.save()
                request.session['2fa_verified'] = True
                codes = TwoFactorBackupCode.generate_for_user(request.user)
                request.session['backup_codes'] = codes
                log_action(request, request.user, '2fa_enabled')
                messages.success(request, 'Weryfikacja dwuetapowa została włączona.')
                return redirect('accounts:show_backup_codes')
            else:
                form.add_error('code', 'Nieprawidłowy kod. Spróbuj ponownie.')
    else:
        form = TOTPVerifyForm()

    return render(request, 'accounts/setup_2fa.html', {
        'form': form,
        'qr_b64': qr_b64,
        'secret': profile.totp_secret,
    })


@login_required
def show_backup_codes(request):
    codes = request.session.pop('backup_codes', [])
    if not codes:
        return redirect('accounts:settings')
    return render(request, 'accounts/backup_codes.html', {'codes': codes})


@login_required
def regenerate_backup_codes(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if not profile.two_factor_enabled:
        return redirect('accounts:settings')

    if request.method == 'POST':
        form = TOTPVerifyForm(request.POST)
        if form.is_valid():
            totp = pyotp.TOTP(profile.totp_secret)
            if totp.verify(form.cleaned_data['code']):
                codes = TwoFactorBackupCode.generate_for_user(request.user)
                request.session['backup_codes'] = codes
                return redirect('accounts:show_backup_codes')
            else:
                form.add_error('code', 'Nieprawidłowy kod TOTP. Spróbuj ponownie.')
    else:
        form = TOTPVerifyForm()

    return render(request, 'accounts/regenerate_backup_codes.html', {'form': form})


@login_required
def disable_2fa(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = TOTPVerifyForm(request.POST)
        if form.is_valid():
            totp = pyotp.TOTP(profile.totp_secret)
            if totp.verify(form.cleaned_data['code']):
                profile.two_factor_enabled = False
                profile.totp_secret = ''
                profile.save()
                TwoFactorBackupCode.objects.filter(user=request.user).delete()
                request.session.pop('2fa_verified', None)
                log_action(request, request.user, '2fa_disabled')
                messages.success(request, 'Weryfikacja dwuetapowa została wyłączona.')
                return redirect('accounts:settings')
            else:
                form.add_error('code', 'Nieprawidłowy kod.')
    else:
        form = TOTPVerifyForm()
    return render(request, 'accounts/disable_2fa.html', {'form': form})


@ratelimit(key='user_or_ip', rate='5/m', method='POST', block=True)
def verify_2fa(request):
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if not profile.two_factor_enabled:
        return redirect('blog:post_list')

    raw_next = request.GET.get('next') or request.POST.get('next') or '/'
    next_url = raw_next if url_has_allowed_host_and_scheme(
        raw_next, allowed_hosts={request.get_host()}
    ) else '/'

    if request.method == 'POST':
        form = TOTPVerifyForm(request.POST)
        if form.is_valid():
            totp = pyotp.TOTP(profile.totp_secret)
            code = form.cleaned_data['code']
            if totp.verify(code):
                request.session['2fa_verified'] = True
                return redirect(next_url)
            elif TwoFactorBackupCode.verify_and_consume(request.user, code):
                request.session['2fa_verified'] = True
                log_action(request, request.user, 'backup_code_used')
                messages.warning(request, 'Zalogowano przy użyciu kodu zapasowego.')
                return redirect(next_url)
            else:
                log_action(request, request.user, '2fa_failed')
                form.add_error('code', 'Nieprawidłowy kod.')
    else:
        form = TOTPVerifyForm()

    return render(request, 'accounts/verify_2fa.html', {'form': form, 'next': next_url})
