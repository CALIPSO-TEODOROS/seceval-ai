from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse, HttpResponse
from users.views import web_ui_view, login_page_view


def api_root(request):
    if 'text/html' in request.headers.get('Accept', ''):
        html_content = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Framework d'Évaluation de Sécurité Web (IA)</title>
    <style>
        :root {
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent: #38bdf8;
            --accent-hover: #0284c7;
            --code-bg: #090d16;
        }
        body {
            font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            margin: 0;
            padding: 40px 20px;
            display: flex;
            justify-content: center;
        }
        .container {
            max-width: 800px;
            width: 100%;
        }
        .header {
            background: var(--card-bg);
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.3);
            border: 1px solid rgba(255,255,255,0.1);
            margin-bottom: 24px;
        }
        h1 {
            color: var(--accent);
            margin-top: 0;
            font-size: 1.8rem;
        }
        p {
            line-height: 1.6;
            color: var(--text-muted);
        }
        .endpoint-card {
            background: var(--card-bg);
            padding: 20px 30px;
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.1);
            margin-bottom: 16px;
        }
        h2 {
            font-size: 1.3rem;
            margin-top: 0;
            color: var(--text-main);
        }
        ul {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        li {
            padding: 10px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        li:last-child {
            border-bottom: none;
        }
        a {
            color: var(--accent);
            text-decoration: none;
            font-weight: 500;
            background: var(--code-bg);
            padding: 6px 12px;
            border-radius: 6px;
            border: 1px solid rgba(56, 189, 248, 0.2);
            transition: all 0.2s ease;
        }
        a:hover {
            background: var(--accent);
            color: #0f172a;
        }
        .badge {
            background: rgba(56, 189, 248, 0.1);
            color: var(--accent);
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.85rem;
            font-family: monospace;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ Framework d'Évaluation de Sécurité Web (IA)</h1>
            <p>Plateforme automatique d'évaluations de sécurité pilotée par agent IA. Le module <strong>Gestion des utilisateurs</strong> est actif.</p>
        </div>

        <div class="endpoint-card">
            <h2>📌 Application Web & Endpoints</h2>
            <ul>
                <li>
                    <span>Interface Web Interactive</span>
                    <a href="/web/" target="_self">💻 /web/</a>
                </li>
                <li>
                    <span>Page de Connexion Dédiée</span>
                    <a href="/web/login/" target="_self">🔐 /web/login/</a>
                </li>
                <li>
                    <span>Administration Django</span>
                    <a href="/admin/" target="_blank">/admin/</a>
                </li>
                <li>
                    <span>Inscription d'un utilisateur <span class="badge">POST</span></span>
                    <span class="badge">/api/users/register/</span>
                </li>
                <li>
                    <span>Connexion d'un utilisateur <span class="badge">POST</span></span>
                    <span class="badge">/api/users/login/</span>
                </li>
                <li>
                    <span>Déconnexion d'un utilisateur <span class="badge">POST</span></span>
                    <span class="badge">/api/users/logout/</span>
                </li>
                <li>
                    <span>Consultation & Modification du Profil <span class="badge">GET / PATCH</span></span>
                    <span class="badge">/api/users/profile/</span>
                </li>
            </ul>
        </div>
    </div>
</body>
</html>"""
        return HttpResponse(html_content, content_type='text/html; charset=utf-8')

    return JsonResponse({
        'message': 'Bienvenue sur le Framework d\'Évaluation de Sécurité Web (IA)',
        'version': '1.0.0',
        'web_ui': '/web/',
        'login_page': '/web/login/',
        'endpoints': {
            'admin': '/admin/',
            'users': {
                'register': '/api/users/register/',
                'login': '/api/users/login/',
                'logout': '/api/users/logout/',
                'profile': '/api/users/profile/',
            }
        }
    }, json_dumps_params={'ensure_ascii': False, 'indent': 2})


urlpatterns = [
    path('', api_root, name='api-root'),
    path('web/', web_ui_view, name='web-ui-direct'),
    path('web/dashboard/', web_ui_view, name='web-dashboard-alias'),
    path('web/login/', login_page_view, name='login-page-direct'),

    path('admin/', admin.site.urls),
    path('api/users/', include('users.urls')),
    path('api/projects/', include('projects.urls')),
    path('api/audits/', include('audits.urls')),
    path('api/recon/', include('recon.urls')),
    path('api/vulns/', include('vulns.urls')),
    path('api/reports/', include('reports.urls')),
    path('api/notifications/', include('notifications_app.urls')),
    path('api/logs/', include('logs_app.urls')),
]

from django.conf import settings
from django.conf.urls.static import static

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)










