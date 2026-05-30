from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name="profile",
        on_delete=models.CASCADE,
        primary_key=True,
        db_column="user_id",
    )
    school = models.CharField(max_length=80, blank=True, default="")
    year = models.IntegerField(null=True, blank=True)
    nickname = models.CharField(max_length=30, blank=True, default="")
    address = models.CharField(max_length=255, blank=True, default="")
    home_location = gis_models.PointField(srid=4326, null=True, blank=True)
    address_geocode_status = models.CharField(
        max_length=20,
        blank=True,
        default="not_provided",
    )
    address_geocode_error = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "user_profile"
        verbose_name = "사용자 프로필"
        verbose_name_plural = "사용자 프로필"

    def __str__(self) -> str:
        return str(self.user)


def get_user_profile(user):
    profile, _created = UserProfile.objects.get_or_create(user=user)
    return profile
