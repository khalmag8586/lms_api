from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import JsonResponse, HttpResponse
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.cache import cache

from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import (
    generics,
    status,
)
from rest_framework.parsers import MultiPartParser
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.parsers import JSONParser

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

import uuid
import csv
import logging
import json
import string
import random
from io import TextIOWrapper


from user.models import (
    User,
)
from user.serializers import (
    UserSerializer,
    UserMeSerializer,
    UserImageSerializer,
    UserCoverSerializer,
    UserDeleteSerializer,
    UserDialogSerializer,
    UserGenderChoiceSerializer,
    UserTypeChoiceSerializer,
)

from user.filters import UserFilter

from lms_api.pagination import StandardResultsSetPagination
from lms_api.utils import get_or_set_cache, cache_response, clear_cache_key
from lms_api.custom_permissions import HasPermissionOrInGroupWithPermission


# User login view
class LoginView(APIView):
    # Primary login view
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        identifier = request.data.get("identifier")  # Field for email or phone number
        password = request.data.get("password")

        # Filter using Q objects to match either email or phone_number
        user = User.objects.filter(
            Q(email=identifier) | Q(mobile_number=identifier)
        ).first()

        if user is None:
            raise AuthenticationFailed(
                _("Email or phone number or password is invalid")
            )
        if user.is_staff == False:
            raise AuthenticationFailed(
                _("Email or phone number or password is invalid!!!")
            )
        if not user.is_active:
            raise AuthenticationFailed(_("User account is inactive"))
        if user.is_deleted == True:
            raise AuthenticationFailed(_("This user is deleted"))
        if not user.check_password(password):
            raise AuthenticationFailed(
                _("Email or phone number or password is invalid")
            )

        refresh = RefreshToken.for_user(user)
        response = Response()
        # Extract group names and convert them to a list of strings
        group_names = list(user.groups.values_list("name", flat=True))
        user_permissions_names = list(
            user.user_permissions.values_list("codename", flat=True)
        )

        response.data = {
            "identifier": (
                user.email if user.email == identifier else user.mobile_number
            ),
            "groups": group_names,
            "user_permissions": user_permissions_names,
            "name": user.name,
            "name_ar": user.name_ar,
            "user_type": user.user_type,
            "is_staff": user.is_staff,
            "access_token": str(refresh.access_token),
            # "refresh_token": str(refresh),
        }
        return response


class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "user.add_user"

    def perform_create(self, serializer):
        # Capitalize the user's name before saving
        name = serializer.validated_data.get("name", "")
        capitalized_name = name.lower()
        serializer.save(name=capitalized_name)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(
            {"detail": _("User created successfully")}, status=status.HTTP_201_CREATED
        )


@method_decorator(cache_page(60 * 10), name="dispatch")  # 10 mins
class UserListView(generics.ListAPIView):
    queryset = User.objects.filter(
        is_deleted=False, is_superuser=False, is_staff=True
    ).order_by("-created_at")
    serializer_class = UserSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "user.view_user"

    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = UserFilter
    search_fields = ["name", "name_ar", "mobile_number", "email", "identification"]
    ordering_fields = [
        "name",
        "-name",
        "name_ar",
        "-name_ar",
        "created_at",
        "-created_at",
    ]


@method_decorator(cache_page(60 * 10), name="dispatch")  # 10 mins
class DeletedUserView(generics.ListAPIView):
    queryset = User.objects.filter(is_deleted=True).order_by("-created_at")
    serializer_class = UserSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "user.view_user"
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = UserFilter
    search_fields = ["name", "name_ar", "mobile_number", "email", "identification"]
    ordering_fields = [
        "name",
        "-name",
        "name_ar",
        "-name_ar",
        "created_at",
        "-created_at",
    ]


class UserRetrieveView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "user.view_user"
    lookup_field = "id"

    def get_queryset(self):
        return User.objects.filter(is_deleted=False)

    # def get_object(self):
    #     user_id = self.request.query_params.get("user_id")
    #     user = get_object_or_404(self.get_queryset(), id=user_id)
    #     return user
    def get_object(self):
        user_id = self.request.query_params.get("user_id")
        cache_key = f"user_detail_{user_id}"
        return get_or_set_cache(
            cache_key,
            lambda: get_object_or_404(self.get_queryset(), id=user_id),
            timeout=300,
        )


class UploadUserPhotoView(generics.UpdateAPIView):
    serializer_class = UserImageSerializer
    authentication_classes = [JWTAuthentication]
    # permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_classes = [IsAuthenticated]
    # permission_codename='user.change_user'

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.action = self.request.method.lower()

    @action(methods=["POST"], detail=True, url_path="upload-image")
    def upload_image(self, request, pk=None):
        user = self.request.user
        serializer = self.get_serializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_serializer_class(self):
        if self.action == "upload_image":
            return UserImageSerializer
        return self.serializer_class

    def update(self, request, *args, **kwargs):
        user = self.request.user  # Get the user from the JWT token
        serializer = self.get_serializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            user.resize_and_save_avatar()
            return Response(
                {"detail": _("Your photo changed successfully")},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UploadUserCoverView(generics.UpdateAPIView):
    serializer_class = UserCoverSerializer
    authentication_classes = [JWTAuthentication]
    # permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_classes = [IsAuthenticated]
    # permission_codename='user.change_user'

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.action = self.request.method.lower()

    @action(methods=["POST"], detail=True, url_path="upload-image")
    def upload_image(self, request, pk=None):
        user = self.request.user
        serializer = self.get_serializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_serializer_class(self):
        if self.action == "upload_image":
            return UserCoverSerializer
        return self.serializer_class

    def update(self, request, *args, **kwargs):
        user = self.request.user  # Get the user from the JWT token
        serializer = self.get_serializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"detail": _("Your cover photo changed successfully")},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ManagerUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserMeSerializer
    authentication_classes = [JWTAuthentication]
    # permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_classes = [IsAuthenticated]
    # permission_codename = "user.change_user"

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):

        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        clear_cache_key(f"user_detail_{instance.id}")

        return Response(
            {"detail": _("Your data Updated successfully")}, status=status.HTTP_200_OK
        )


class UserDeleteTemporaryView(generics.UpdateAPIView):
    serializer_class = UserDeleteSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "user.delete_user"

    def update(self, request, *args, **kwargs):
        user_ids = request.data.get("user_id", [])
        partial = kwargs.pop("partial", False)
        is_deleted = request.data.get("is_deleted")

        if is_deleted == False:
            return Response(
                {"detail": _("These users are not deleted")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        for user_id in user_ids:
            instance = get_object_or_404(User, id=user_id)
            if instance.is_deleted:
                return Response(
                    {
                        "detail": _(
                            "User with ID {} is already temp deleted".format(user_id)
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial
            )
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            clear_cache_key(f"user_detail_{user_id}")

        return Response(
            {"detail": _("Users temp deleted successfully")}, status=status.HTTP_200_OK
        )


class UserRestoreView(generics.RetrieveUpdateAPIView):

    serializer_class = UserDeleteSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "user.change_user"

    def update(self, request, *args, **kwargs):
        user_ids = request.data.get("user_id", [])
        partial = kwargs.pop("partial", False)
        is_deleted = request.data.get("is_deleted")

        if is_deleted == True:
            return Response(
                {"detail": _("users are already deleted")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        for user_id in user_ids:
            instance = get_object_or_404(User, id=user_id)
            if instance.is_deleted == False:
                return Response(
                    {"detail": _("User with ID {} is not deleted".format(user_id))},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial
            )
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            clear_cache_key(f"user_detail_{user_id}")

        return Response(
            {"detail": _("Users restored successfully")}, status=status.HTTP_200_OK
        )


class UserUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "user.change_user"
    lookup_field = "id"

    def get_object(self):
        user_id = self.request.query_params.get("user_id")
        user = get_object_or_404(User, id=user_id)
        return user

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        clear_cache_key(f"user_detail_{instance.id}")

        return Response(
            {"detail": _("User Updated successfully")}, status=status.HTTP_200_OK
        )


class UserDeleteView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "user.delete_user"

    def delete(self, request, format=None):
        data = JSONParser().parse(request)
        user_id_list = data.get("user_id", [])

        if not user_id_list:
            return Response(
                {"detail": _("No user IDs provided for deletion")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if each UUID is valid
        for uid in user_id_list:
            clear_cache_key(f"user_detail_{uid}")

            try:
                uuid.UUID(uid.strip())
            except ValueError:
                raise ValidationError(_("'{}' is not a valid UUID.".format(uid)))

        users = User.objects.filter(id__in=user_id_list)
        if not users.exists():
            return Response(
                {"detail": _("No users found")},
                status=status.HTTP_404_NOT_FOUND,
            )

        users.delete()

        return Response(
            {"detail": _("Users permanently deleted successfully")},
            status=status.HTTP_204_NO_CONTENT,
        )


# User Dialogs
class UserDialogView(generics.ListAPIView):
    serializer_class = UserDialogSerializer
    queryset = User.objects.filter(is_deleted=False, is_superuser=False)
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]


# class UserGenderDialogView(APIView):
#     authentication_classes = [JWTAuthentication]
#     permission_classes = [IsAuthenticated]

#     def get(self, request, *args, **kwargs):
#         # Define the gender choices here
#         gender_choices = [
#             {"value": "male", "display": _("Male")},
#             {"value": "female", "display": _("Female")},
#         ]


#         serializer = UserGenderChoiceSerializer(gender_choices, many=True)
#         return Response(serializer.data, status=status.HTTP_200_OK)
class UserGenderDialogView(APIView):
    @cache_response(timeout=1800, key_prefix="gender_dialog")
    def get(self, request, *args, **kwargs):
        return Response(
            [
                {"value": "male", "display": _("Male")},
                {"value": "female", "display": _("Female")},
            ]
        )


# class UserTypeDialogView(APIView):
#     authentication_classes = [JWTAuthentication]
#     permission_classes = [IsAuthenticated]

#     def get(self, request, *args, **kwargs):
#         # Define the gender choices here
#         gender_choices = [
#             {"value": "employee", "display": _("Employee")},
#             {"value": "teacher", "display": _("Teacher")},
#             {"value": "assistant", "display": _("Assistant")},
#             {"value": "parent", "display": _("Parent")},
#             {"value": "student", "display": _("Student")},
#         ]

#         serializer = UserTypeChoiceSerializer(gender_choices, many=True)
#         return Response(serializer.data, status=status.HTTP_200_OK)


class UserTypeDialogView(APIView):
    def get(self, request, *args, **kwargs):
        def fetch_user_types():
            return [
                {"value": "employee", "display": _("Employee")},
                {"value": "teacher", "display": _("Teacher")},
                {"value": "assistant", "display": _("Assistant")},
                {"value": "parent", "display": _("Parent")},
                {"value": "student", "display": _("Student")},
            ]

        data = get_or_set_cache("user_type_dialog", fetch_user_types, timeout=3600)
        return Response(data)


logger = logging.getLogger(__name__)


@csrf_exempt
def forgot_password(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)  # Parse the JSON request body
            email = data.get("email")
            if not email:
                return JsonResponse(
                    {"detail": _("Email is required.")},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            customer = get_object_or_404(User, email=email)

            # Generate a new password
            def generate_password(length=8):
                lowercase_chars = string.ascii_lowercase
                uppercase_chars = string.ascii_uppercase
                digit_chars = string.digits

                password = [
                    random.choice(lowercase_chars),
                    random.choice(uppercase_chars),
                    random.choice(digit_chars),
                ]

                for _ in range(length - 3):
                    password.append(
                        random.choice(lowercase_chars + uppercase_chars + digit_chars)
                    )

                random.shuffle(password)

                return "".join(password)

            new_password = generate_password(8)

            # Update user's password
            customer.set_password(new_password)
            customer.save()

            # Send email with new password
            send_mail(
                "Password Reset",
                f"Your new password is: {new_password}",
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )

            logger.info(f"Password reset for {email} successful.")
            return JsonResponse(
                {"detail": _("Password reset email sent successfully.")}
            )
        except Exception as e:
            logger.error(f"Error during password reset: {str(e)}")
            return JsonResponse(
                {"detail": _("An error occurred. Please try again later.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    else:
        return JsonResponse(
            {"detail": _("Method not allowed.")},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )


class ExportUserCSVTemplateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "user.add_user"

    def get(self, request, *args, **kwargs):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=user_template.csv"

        writer = csv.writer(response)
        writer.writerow(
            [
                "email",
                "password",
                "name",
                "name_ar",
                "identification",
                "birthdate",
                "position",
                "gender",
                "user_type",
                "education",
                "home_address",
                "mobile_number",
            ]
        )
        return response


class ImportUserCSVView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "user.add_user"
    parser_classes = [MultiPartParser]

    def post(self, request, *args, **kwargs):
        csv_file = request.FILES.get("file")
        if not csv_file or not csv_file.name.endswith(".csv"):
            return Response({"detail": _("Invalid file format.")}, status=400)

        decoded_file = TextIOWrapper(csv_file.file, encoding="utf-8")
        reader = csv.DictReader(decoded_file)

        rows = list(reader)
        if not rows:
            return Response(
                {"detail": _("The uploaded CSV file is empty.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_users = []
        errors = []

        for i, row in enumerate(rows, start=1):
            try:
                # Check for duplicates
                if User.objects.filter(email=row["email"]).exists():
                    raise ValueError(f"Row {i}: Email already exists.")

                if User.objects.filter(mobile_number=row["mobile_number"]).exists():
                    raise ValueError(f"Row {i}: Mobile number already exists.")

                # Validate email
                validate_email(row["email"])

                # Validate password
                password = row["password"]
                if len(password) < 8:
                    raise ValueError(f"Row {i}: Password too short.")
                if not any(c.isupper() for c in password):
                    raise ValueError(
                        f"Row {i}: Password must contain uppercase letter."
                    )
                if not any(c.islower() for c in password):
                    raise ValueError(
                        f"Row {i}: Password must contain lowercase letter."
                    )
                if not any(c.isdigit() for c in password):
                    raise ValueError(f"Row {i}: Password must contain digit.")

                # Create the user
                user = User.objects.create_user(
                    email=row["email"],
                    password=password,
                    name=row["name"],
                    name_ar=row["name_ar"],
                    identification=row["identification"],
                    birthdate=row["birthdate"],
                    position=row["position"],
                    gender=row["gender"],
                    user_type=row["user_type"],
                    education=row.get("education", ""),
                    home_address=row.get("home_address", ""),
                    mobile_number=row["mobile_number"],
                )

                created_users.append(user.email)

            except Exception as e:
                errors.append(str(e))

        if not errors:
            return Response(
                {
                    "detail": _("Data imported successfully."),
                    "created_users": created_users,
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {
                    "detail": _("Data failed to import. See errors below."),
                    "created_users": created_users,
                    "errors": errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
