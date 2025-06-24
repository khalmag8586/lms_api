from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from graphene_django.views import GraphQLView
from django.views.decorators.csrf import csrf_exempt

from lms_api.schema import schema
urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
]
urlpatterns += i18n_patterns(
    path("admin/", admin.site.urls),
    # path('api/project_setup/',include('apps.project_setup.urls')),
    path("auth/", include("djoser.urls")),
    # path("auth/", include("djoser.urls.jwt")),
    # path("auth/", include("djoser.urls.authtoken")),
    path("graphql/", csrf_exempt(GraphQLView.as_view(graphiql=True, schema=schema))),

    path("api/users/", include("user.urls")),
    path("api/permissions/", include("apps.a1_permissions_api.urls")),
    path("api/about_us/", include("apps.a2_about_us.urls")),
    path("api/contact_us/", include("apps.a3_contact_us.urls")),
    path("api/edusystem/", include("apps.a4_eduSys.urls")),

)

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
    urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.STATIC_ROOT,
    )
