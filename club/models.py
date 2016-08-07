from django.db import models
from django.core import validators
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.core.urlresolvers import reverse

from core.models import User, MetaGroup, Group
from subscription.models import Subscriber

# Create your models here.

class Club(models.Model):
    """
    The Club class, made as a tree to allow nice tidy organization
    """
    name = models.CharField(_('name'), max_length=30)
    parent = models.ForeignKey('Club', related_name='children', null=True, blank=True)
    unix_name = models.CharField(_('unix name'), max_length=30, unique=True,
            validators=[
                validators.RegexValidator(
                    r'^[a-z0-9][a-z0-9._-]*[a-z0-9]$',
                    _('Enter a valid unix name. This value may contain only '
                        'letters, numbers ./-/_ characters.')
                    ),
                ],
            error_messages={
                'unique': _("A club with that unix name already exists."),
                },
            )
    address = models.CharField(_('address'), max_length=254)
    # email = models.EmailField(_('email address'), unique=True) # This should, and will be generated automatically
    owner_group = models.ForeignKey(Group, related_name="owned_club",
                                    default=settings.SITH_GROUPS['root']['id'])
    edit_groups = models.ManyToManyField(Group, related_name="editable_club", blank=True)
    view_groups = models.ManyToManyField(Group, related_name="viewable_club", blank=True)

    def check_loop(self):
        """Raise a validation error when a loop is found within the parent list"""
        objs = []
        cur = self
        while cur.parent is not None:
            if cur in objs:
                raise ValidationError(_('You can not make loops in clubs'))
            objs.append(cur)
            cur = cur.parent

    def clean(self):
        self.check_loop()

    def save(self):
        if self.id is None:
            MetaGroup(name=self.unix_name+settings.SITH_BOARD_SUFFIX).save()
            MetaGroup(name=self.unix_name+settings.SITH_MEMBER_SUFFIX).save()
        super(Club, self).save()

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('club:club_view', kwargs={'club_id': self.id})

    def get_display_name(self):
        return self.name

    def is_owned_by(self, user):
        """
        Method to see if that object can be super edited by the given user
        """
        if user.is_in_group(settings.SITH_MAIN_BOARD_GROUP):
            return True
        return False

    def can_be_edited_by(self, user):
        """
        Method to see if that object can be edited by the given user
        """
        ms = self.get_membership_for(user)
        if ms is not None:
            return True
        return False

    def can_be_viewed_by(self, user):
        """
        Method to see if that object can be seen by the given user
        """
        sub = Subscriber.objects.filter(pk=user.pk).first()
        if sub is None:
            return False
        return sub.is_subscribed()

    def get_membership_for(self, user):
        """
        Returns the current membership the given user
        """
        return self.members.filter(user=user.id).filter(end_date=None).first()

class Membership(models.Model):
    """
    The Membership class makes the connection between User and Clubs

    Both Users and Clubs can have many Membership objects:
       - a user can be a member of many clubs at a time
       - a club can have many members at a time too

    A User is currently member of all the Clubs where its Membership has an end_date set to null/None.
    Otherwise, it's a past membership kept because it can be very useful to see who was in which Club in the past.
    """
    user = models.ForeignKey(User, verbose_name=_('user'), related_name="membership", null=False, blank=False)
    club = models.ForeignKey(Club, verbose_name=_('club'), related_name="members", null=False, blank=False)
    start_date = models.DateField(_('start date'), auto_now=True)
    end_date = models.DateField(_('end date'), null=True, blank=True)
    role = models.IntegerField(_('role'), choices=sorted(settings.SITH_CLUB_ROLES.items()),
            default=sorted(settings.SITH_CLUB_ROLES.items())[0][0])
    description = models.CharField(_('description'), max_length=30, null=False, blank=True)

    def clean(self):
        sub = Subscriber.objects.filter(pk=self.user.pk).first()
        if sub is None or not sub.is_subscribed():
            raise ValidationError(_('User must be subscriber to take part to a club'))
        if Membership.objects.filter(user=self.user).filter(club=self.club).filter(end_date=None).exists():
            raise ValidationError(_('User is already member of that club'))

    def __str__(self):
        return self.club.name+' - '+self.user.username+' - '+str(settings.SITH_CLUB_ROLES[self.role])+str(
                " - "+str(_('past member')) if self.end_date is not None else ""
                )

    def get_absolute_url(self):
        return reverse('club:club_members', kwargs={'club_id': self.club.id})

