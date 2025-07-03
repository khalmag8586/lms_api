import string, random
from django.db.models.signals import  post_migrate
from django.dispatch import receiver
from django.utils.text import slugify
from django.apps import apps
from django.db.models import Q
from django.http import JsonResponse

from django.utils.translation import gettext_lazy as _
from rest_framework.views import APIView
from django.contrib.auth.models import Group, Permission



import random
from django.utils.timezone import now


from django.core.cache import cache
from functools import wraps
from rest_framework.response import Response
from rest_framework import status



def get_or_set_cache(key, func, timeout=300):
    """
    Retrieve data from cache or execute the function and cache its result.
    :param key: Cache key
    :param func: Callable that returns the data
    :param timeout: Time to live in seconds
    :return: Cached or newly computed data
    """
    data = cache.get(key)
    if data is None:
        data = func()
        cache.set(key, data, timeout)
    return data


def clear_cache_key(key):
    """
    Delete a cache key manually.
    """
    cache.delete(key)


def cache_response(timeout=300, key_prefix=""):
    """
    Decorator for DRF views (GET methods only) to cache their response.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(self, request, *args, **kwargs):
            key = f"{key_prefix}:{request.get_full_path()}"
            cached = cache.get(key)
            if cached:
                return Response(cached)

            response = view_func(self, request, *args, **kwargs)
            if isinstance(response, Response) and response.status_code == 200:
                cache.set(key, response.data, timeout)
            return response
        return _wrapped_view
    return decorator

########################################################


def random_string_generator(size=10, chars=string.ascii_lowercase + string.digits):
    return "".join(random.choice(chars) for _ in range(size))


def unique_slug_generator(instance, new_slug=None):
    if new_slug is not None:
        slug = new_slug
    else:
        slug = slugify(instance.name)
    Klass = instance.__class__
    max_length = Klass._meta.get_field("slug").max_length
    slug = slug[:max_length]
    qs_exists = Klass.objects.filter(slug=slug).exists()

    if qs_exists:
        new_slug = "{slug}-{randstr}".format(
            slug=slug[: max_length - 5], randstr=random_string_generator(size=4)
        )

        return unique_slug_generator(instance, new_slug=new_slug)
    return slug


class CheckFieldValueExistenceView(APIView):
    def get(self, request):
        field_name = request.GET.get("field")
        field_value = request.GET.get("value")

        if not field_name or not field_value:
            return JsonResponse(
                {
                    "detail": _(
                        "Field name and value are required in the query parameters."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        app_models = apps.get_models()

        # List to store model names where the field exists
        existing_models = []

        # Iterate through all models and check if the field exists
        for model in app_models:
            if hasattr(model, field_name):
                # Use Q objects to handle fields with the same name
                filter_query = Q(**{field_name: field_value})
                exists = model.objects.filter(filter_query).exists()
                if exists:
                    existing_models.append(model.__name__)

        if existing_models:
            message = _(
                "The value '{}' already exists in the following models: {}"
            ).format(field_value, ", ".join(existing_models))
            return JsonResponse({"is_exist": True, "detail": message}, status=status.HTTP_403_FORBIDDEN)
        else:
            message = _("The value '{}' does not exist in any model.").format(
                field_value
            )
            return JsonResponse({"is_exist": False, "detail": message}, status=status.HTTP_200_OK)


@receiver(post_migrate)
def create_initial_groups(sender, **kwargs):
    if sender.name == "user":
        # Create or get the 'admins' group
        admin_group, created = Group.objects.get_or_create(name="admins")

        # Assign all permissions to the 'admins' group
        all_permissions = Permission.objects.all()
        admin_group.permissions.set(all_permissions)

        # Create or get the 'normal' group
        normal_group, created = Group.objects.get_or_create(name="normal")

        # Assign view permissions to the 'normal' group
        # Assuming 'view' permissions are represented by the 'view' codename
        view_permissions = Permission.objects.filter(codename__startswith="view")
        normal_group.permissions.set(view_permissions)
