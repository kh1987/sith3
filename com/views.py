#
# Copyright 2016,2017
# - Skia <skia@libskia.so>
# - Sli <antoine@bartuccio.fr>
#
# Ce fichier fait partie du site de l'Association des Étudiants de l'UTBM,
# http://ae.utbm.fr.
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License a published by the Free Software
# Foundation; either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Sofware Foundation, Inc., 59 Temple
# Place - Suite 330, Boston, MA 02111-1307, USA.
#
#
import itertools
from datetime import timedelta
from smtplib import SMTPRecipientsRefused

from django import forms
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Exists, Max, OuterRef
from django.forms.models import modelform_factory
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, ListView, View
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from club.models import Club, Mailing
from com.models import News, NewsDate, Poster, Screen, Sith, Weekmail, WeekmailArticle
from core.models import Notification, User
from core.views import (
    CanCreateMixin,
    CanEditMixin,
    CanEditPropMixin,
    CanViewMixin,
    QuickNotifMixin,
    TabedViewMixin,
)
from core.views.forms import SelectDateTime
from core.views.widgets.markdown import MarkdownInput

# Sith object

sith = Sith.objects.first


class PosterForm(forms.ModelForm):
    class Meta:
        model = Poster
        fields = [
            "name",
            "file",
            "club",
            "screens",
            "date_begin",
            "date_end",
            "display_time",
        ]
        widgets = {"screens": forms.CheckboxSelectMultiple}
        help_texts = {"file": _("Format: 16:9 | Resolution: 1920x1080")}

    date_begin = forms.DateTimeField(
        label=_("Start date"),
        widget=SelectDateTime,
        required=True,
        initial=timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    date_end = forms.DateTimeField(
        label=_("End date"), widget=SelectDateTime, required=False
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if self.user and not self.user.is_com_admin:
            self.fields["club"].queryset = Club.objects.filter(
                id__in=self.user.clubs_with_rights
            )
            self.fields.pop("display_time")


class ComTabsMixin(TabedViewMixin):
    def get_tabs_title(self):
        return _("Communication administration")

    def get_list_of_tabs(self):
        tab_list = []
        tab_list.append(
            {"url": reverse("com:weekmail"), "slug": "weekmail", "name": _("Weekmail")}
        )
        tab_list.append(
            {
                "url": reverse("com:weekmail_destinations"),
                "slug": "weekmail_destinations",
                "name": _("Weekmail destinations"),
            }
        )
        tab_list.append(
            {"url": reverse("com:info_edit"), "slug": "info", "name": _("Info message")}
        )
        tab_list.append(
            {
                "url": reverse("com:alert_edit"),
                "slug": "alert",
                "name": _("Alert message"),
            }
        )
        tab_list.append(
            {
                "url": reverse("com:mailing_admin"),
                "slug": "mailings",
                "name": _("Mailing lists administration"),
            }
        )
        tab_list.append(
            {
                "url": reverse("com:poster_list"),
                "slug": "posters",
                "name": _("Posters list"),
            }
        )
        tab_list.append(
            {
                "url": reverse("com:screen_list"),
                "slug": "screens",
                "name": _("Screens list"),
            }
        )
        return tab_list


class IsComAdminMixin(View):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_com_admin:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class ComEditView(ComTabsMixin, CanEditPropMixin, UpdateView):
    model = Sith
    template_name = "core/edit.jinja"

    def get_object(self, queryset=None):
        return Sith.objects.first()


class AlertMsgEditView(ComEditView):
    form_class = modelform_factory(
        Sith, fields=["alert_msg"], widgets={"alert_msg": MarkdownInput}
    )
    current_tab = "alert"
    success_url = reverse_lazy("com:alert_edit")


class InfoMsgEditView(ComEditView):
    form_class = modelform_factory(
        Sith, fields=["info_msg"], widgets={"info_msg": MarkdownInput}
    )
    current_tab = "info"
    success_url = reverse_lazy("com:info_edit")


class WeekmailDestinationEditView(ComEditView):
    fields = ["weekmail_destinations"]
    current_tab = "weekmail_destinations"
    success_url = reverse_lazy("com:weekmail_destinations")


# News


class NewsForm(forms.ModelForm):
    class Meta:
        model = News
        fields = ["type", "title", "club", "summary", "content", "author"]
        widgets = {
            "author": forms.HiddenInput,
            "type": forms.RadioSelect,
            "summary": MarkdownInput,
            "content": MarkdownInput,
        }

    start_date = forms.DateTimeField(
        label=_("Start date"), widget=SelectDateTime, required=False
    )
    end_date = forms.DateTimeField(
        label=_("End date"), widget=SelectDateTime, required=False
    )
    until = forms.DateTimeField(label=_("Until"), widget=SelectDateTime, required=False)

    automoderation = forms.BooleanField(label=_("Automoderation"), required=False)

    def clean(self):
        self.cleaned_data = super().clean()
        if self.cleaned_data["type"] != "NOTICE":
            if not self.cleaned_data["start_date"]:
                self.add_error(
                    "start_date", ValidationError(_("This field is required."))
                )
            if not self.cleaned_data["end_date"]:
                self.add_error(
                    "end_date", ValidationError(_("This field is required."))
                )
            if (
                not self.has_error("start_date")
                and not self.has_error("end_date")
                and self.cleaned_data["start_date"] > self.cleaned_data["end_date"]
            ):
                self.add_error(
                    "end_date",
                    ValidationError(_("An event cannot end before its beginning.")),
                )
            if self.cleaned_data["type"] == "WEEKLY" and not self.cleaned_data["until"]:
                self.add_error("until", ValidationError(_("This field is required.")))
        return self.cleaned_data

    def save(self, *args, **kwargs):
        ret = super().save()
        self.instance.dates.all().delete()
        if self.instance.type == "EVENT" or self.instance.type == "CALL":
            NewsDate(
                start_date=self.cleaned_data["start_date"],
                end_date=self.cleaned_data["end_date"],
                news=self.instance,
            ).save()
        elif self.instance.type == "WEEKLY":
            start_date = self.cleaned_data["start_date"]
            end_date = self.cleaned_data["end_date"]
            while start_date <= self.cleaned_data["until"]:
                NewsDate(
                    start_date=start_date, end_date=end_date, news=self.instance
                ).save()
                start_date += timedelta(days=7)
                end_date += timedelta(days=7)
        return ret


class NewsEditView(CanEditMixin, UpdateView):
    model = News
    form_class = NewsForm
    template_name = "com/news_edit.jinja"
    pk_url_kwarg = "news_id"

    def get_initial(self):
        news_date: NewsDate = self.object.dates.order_by("id").first()
        if news_date is None:
            return {"start_date": None, "end_date": None}
        return {"start_date": news_date.start_date, "end_date": news_date.end_date}

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid() and "preview" not in request.POST:
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        self.object = form.save()
        if form.cleaned_data["automoderation"] and self.request.user.is_com_admin:
            self.object.moderator = self.request.user
            self.object.is_moderated = True
            self.object.save()
        else:
            self.object.is_moderated = False
            self.object.save()
            unread_notif_subquery = Notification.objects.filter(
                user=OuterRef("pk"), type="NEWS_MODERATION", viewed=False
            )
            for user in User.objects.filter(
                ~Exists(unread_notif_subquery),
                groups__id__in=[settings.SITH_GROUP_COM_ADMIN_ID],
            ):
                Notification.objects.create(
                    user=user,
                    url=self.object.get_absolute_url(),
                    type="NEWS_MODERATION",
                )
        return super().form_valid(form)


class NewsCreateView(CanCreateMixin, CreateView):
    model = News
    form_class = NewsForm
    template_name = "com/news_edit.jinja"

    def get_initial(self):
        init = {"author": self.request.user}
        if "club" not in self.request.GET:
            return init
        init["club"] = Club.objects.filter(id=self.request.GET["club"]).first()
        return init

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid() and "preview" not in request.POST:
            return self.form_valid(form)
        else:
            self.object = form.instance
            return self.form_invalid(form)

    def form_valid(self, form):
        self.object = form.save()
        if form.cleaned_data["automoderation"] and self.request.user.is_com_admin:
            self.object.moderator = self.request.user
            self.object.is_moderated = True
            self.object.save()
        else:
            unread_notif_subquery = Notification.objects.filter(
                user=OuterRef("pk"), type="NEWS_MODERATION", viewed=False
            )
            for user in User.objects.filter(
                ~Exists(unread_notif_subquery),
                groups__id__in=[settings.SITH_GROUP_COM_ADMIN_ID],
            ):
                Notification.objects.create(
                    user=user,
                    url=reverse("com:news_admin_list"),
                    type="NEWS_MODERATION",
                )
        return super().form_valid(form)


class NewsDeleteView(CanEditMixin, DeleteView):
    model = News
    pk_url_kwarg = "news_id"
    template_name = "core/delete_confirm.jinja"
    success_url = reverse_lazy("com:news_admin_list")


class NewsModerateView(CanEditMixin, SingleObjectMixin):
    model = News
    pk_url_kwarg = "news_id"

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if "remove" in request.GET:
            self.object.is_moderated = False
        else:
            self.object.is_moderated = True
        self.object.moderator = request.user
        self.object.save()
        if "next" in self.request.GET:
            return redirect(self.request.GET["next"])
        return redirect("com:news_admin_list")


class NewsAdminListView(CanEditMixin, ListView):
    model = News
    template_name = "com/news_admin_list.jinja"
    queryset = News.objects.all()


class NewsListView(CanViewMixin, ListView):
    model = News
    template_name = "com/news_list.jinja"
    queryset = News.objects.filter(is_moderated=True)

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        kwargs["NewsDate"] = NewsDate
        kwargs["timedelta"] = timedelta
        kwargs["birthdays"] = itertools.groupby(
            User.objects.filter(
                date_of_birth__month=localdate().month,
                date_of_birth__day=localdate().day,
            )
            .filter(role__in=["STUDENT", "FORMER STUDENT"])
            .order_by("-date_of_birth"),
            key=lambda u: u.date_of_birth.year,
        )
        return kwargs


class NewsDetailView(CanViewMixin, DetailView):
    model = News
    template_name = "com/news_detail.jinja"
    pk_url_kwarg = "news_id"


# Weekmail


class WeekmailPreviewView(ComTabsMixin, QuickNotifMixin, CanEditPropMixin, DetailView):
    model = Weekmail
    template_name = "com/weekmail_preview.jinja"
    success_url = reverse_lazy("com:weekmail")
    current_tab = "weekmail"

    def dispatch(self, request, *args, **kwargs):
        self.bad_recipients = []
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if request.POST["send"] == "validate":
            try:
                self.object.send()
                return HttpResponseRedirect(
                    reverse("com:weekmail") + "?qn_weekmail_send_success"
                )
            except SMTPRecipientsRefused as e:
                self.bad_recipients = e.recipients
        elif request.POST["send"] == "clean":
            try:
                self.object.send()  # This should fail
            except SMTPRecipientsRefused as e:
                users = User.objects.filter(email__in=e.recipients)
                for u in users:
                    u.preferences.receive_weekmail = False
                    u.preferences.save()
                self.quick_notif_list += ["qn_success"]
        return super().get(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return self.model.objects.filter(sent=False).order_by("-id").first()

    def get_context_data(self, **kwargs):
        """Add rendered weekmail."""
        kwargs = super().get_context_data(**kwargs)
        kwargs["weekmail_rendered"] = self.object.render_html()
        kwargs["bad_recipients"] = self.bad_recipients
        return kwargs


class WeekmailEditView(ComTabsMixin, QuickNotifMixin, CanEditPropMixin, UpdateView):
    model = Weekmail
    template_name = "com/weekmail.jinja"
    form_class = modelform_factory(
        Weekmail,
        fields=["title", "intro", "joke", "protip", "conclusion"],
        help_texts={"title": _("Delete and save to regenerate")},
        widgets={
            "intro": MarkdownInput,
            "joke": MarkdownInput,
            "protip": MarkdownInput,
            "conclusion": MarkdownInput,
        },
    )
    success_url = reverse_lazy("com:weekmail")
    current_tab = "weekmail"

    def get_object(self, queryset=None):
        weekmail = self.model.objects.filter(sent=False).order_by("-id").first()
        if not weekmail.title:
            now = timezone.now()
            weekmail.title = _("Weekmail of the ") + (
                now + timedelta(days=6 - now.weekday())
            ).strftime("%d/%m/%Y")
            weekmail.save()
        return weekmail

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if "up_article" in request.GET:
            art = get_object_or_404(
                WeekmailArticle, id=request.GET["up_article"], weekmail=self.object
            )
            prev_art = (
                self.object.articles.order_by("rank").filter(rank__lt=art.rank).last()
            )
            if prev_art:
                art.rank, prev_art.rank = prev_art.rank, art.rank
                art.save()
                prev_art.save()
                self.quick_notif_list += ["qn_success"]
        if "down_article" in request.GET:
            art = get_object_or_404(
                WeekmailArticle, id=request.GET["down_article"], weekmail=self.object
            )
            next_art = (
                self.object.articles.order_by("rank").filter(rank__gt=art.rank).first()
            )
            if next_art:
                art.rank, next_art.rank = next_art.rank, art.rank
                art.save()
                next_art.save()
                self.quick_notif_list += ["qn_success"]
        if "add_article" in request.GET:
            art = get_object_or_404(
                WeekmailArticle, id=request.GET["add_article"], weekmail=None
            )
            art.weekmail = self.object
            art.rank = self.object.articles.aggregate(Max("rank"))["rank__max"] or 0
            art.rank += 1
            art.save()
            self.quick_notif_list += ["qn_success"]
        if "del_article" in request.GET:
            art = get_object_or_404(
                WeekmailArticle, id=request.GET["del_article"], weekmail=self.object
            )
            art.weekmail = None
            art.rank = -1
            art.save()
            self.quick_notif_list += ["qn_success"]
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Add orphan articles."""
        kwargs = super().get_context_data(**kwargs)
        kwargs["orphans"] = WeekmailArticle.objects.filter(weekmail=None)
        return kwargs


class WeekmailArticleEditView(
    ComTabsMixin, QuickNotifMixin, CanEditPropMixin, UpdateView
):
    """Edit an article."""

    model = WeekmailArticle
    form_class = modelform_factory(
        WeekmailArticle,
        fields=["title", "club", "content"],
        widgets={"content": MarkdownInput},
    )
    pk_url_kwarg = "article_id"
    template_name = "core/edit.jinja"
    success_url = reverse_lazy("com:weekmail")
    quick_notif_url_arg = "qn_weekmail_article_edit"
    current_tab = "weekmail"


class WeekmailArticleCreateView(QuickNotifMixin, CreateView):
    """Post an article."""

    model = WeekmailArticle
    form_class = modelform_factory(
        WeekmailArticle,
        fields=["title", "club", "content"],
        widgets={"content": MarkdownInput},
    )
    template_name = "core/create.jinja"
    success_url = reverse_lazy("core:user_tools")
    quick_notif_url_arg = "qn_weekmail_new_article"

    def get_initial(self):
        if "club" not in self.request.GET:
            return {}
        return {"club": Club.objects.filter(id=self.request.GET.get("club")).first()}

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        self.object = form.instance
        form.is_valid()  # Valid a first time to populate club field
        m = form.instance.club.get_membership_for(request.user)
        if m is None or m.role <= settings.SITH_MAXIMUM_FREE_ROLE:
            form.add_error(
                "club",
                ValidationError(
                    _(
                        "You must be a board member of the selected club to post in the Weekmail."
                    )
                ),
            )
        if form.is_valid() and "preview" not in request.POST:
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)


class WeekmailArticleDeleteView(CanEditPropMixin, DeleteView):
    """Delete an article."""

    model = WeekmailArticle
    template_name = "core/delete_confirm.jinja"
    success_url = reverse_lazy("com:weekmail")
    pk_url_kwarg = "article_id"


class MailingListAdminView(ComTabsMixin, ListView):
    template_name = "com/mailing_admin.jinja"
    model = Mailing
    current_tab = "mailings"

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_com_admin or request.user.is_root):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        kwargs["moderated"] = self.get_queryset().filter(is_moderated=True).all()
        kwargs["unmoderated"] = self.get_queryset().filter(is_moderated=False).all()
        kwargs["has_moderated"] = len(kwargs["moderated"]) > 0
        kwargs["has_unmoderated"] = len(kwargs["unmoderated"]) > 0
        return kwargs


class MailingModerateView(View):
    def get(self, request, *args, **kwargs):
        mailing = get_object_or_404(Mailing, pk=kwargs["mailing_id"])
        if mailing.can_moderate(request.user):
            mailing.is_moderated = True
            mailing.moderator = request.user
            mailing.save()
            return redirect("com:mailing_admin")

        raise PermissionDenied


class PosterListBaseView(ListView):
    """List communication posters."""

    current_tab = "posters"
    model = Poster
    template_name = "com/poster_list.jinja"

    def dispatch(self, request, *args, **kwargs):
        club_id = kwargs.pop("club_id", None)
        self.club = None
        if club_id:
            self.club = get_object_or_404(Club, pk=club_id)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        if self.request.user.is_com_admin:
            return Poster.objects.all().order_by("-date_begin")
        else:
            return Poster.objects.filter(club=self.club.id)

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        if not self.request.user.is_com_admin:
            kwargs["club"] = self.club
        return kwargs


class PosterCreateBaseView(CreateView):
    """Create communication poster."""

    current_tab = "posters"
    form_class = PosterForm
    template_name = "core/create.jinja"

    def get_queryset(self):
        return Poster.objects.all()

    def dispatch(self, request, *args, **kwargs):
        if "club_id" in kwargs:
            self.club = get_object_or_404(Club, pk=kwargs["club_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        if not self.request.user.is_com_admin:
            kwargs["club"] = self.club
        return kwargs

    def form_valid(self, form):
        if self.request.user.is_com_admin:
            form.instance.is_moderated = True
        return super().form_valid(form)


class PosterEditBaseView(UpdateView):
    """Edit communication poster."""

    pk_url_kwarg = "poster_id"
    current_tab = "posters"
    form_class = PosterForm
    template_name = "com/poster_edit.jinja"

    def get_initial(self):
        return {
            "date_begin": self.object.date_begin.strftime("%Y-%m-%d %H:%M:%S")
            if self.object.date_begin
            else None,
            "date_end": self.object.date_end.strftime("%Y-%m-%d %H:%M:%S")
            if self.object.date_end
            else None,
        }

    def dispatch(self, request, *args, **kwargs):
        if kwargs.get("club_id"):
            try:
                self.club = Club.objects.get(pk=kwargs["club_id"])
            except Club.DoesNotExist as e:
                raise PermissionDenied from e
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Poster.objects.all()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        if hasattr(self, "club"):
            kwargs["club"] = self.club
        return kwargs

    def form_valid(self, form):
        if self.request.user.is_com_admin:
            form.instance.is_moderated = False
        return super().form_valid(form)


class PosterDeleteBaseView(DeleteView):
    """Edit communication poster."""

    pk_url_kwarg = "poster_id"
    current_tab = "posters"
    model = Poster
    template_name = "core/delete_confirm.jinja"

    def dispatch(self, request, *args, **kwargs):
        if kwargs.get("club_id"):
            try:
                self.club = Club.objects.get(pk=kwargs["club_id"])
            except Club.DoesNotExist as e:
                raise PermissionDenied from e
        return super().dispatch(request, *args, **kwargs)


class PosterListView(IsComAdminMixin, ComTabsMixin, PosterListBaseView):
    """List communication posters."""

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        kwargs["app"] = "com"
        return kwargs


class PosterCreateView(IsComAdminMixin, ComTabsMixin, PosterCreateBaseView):
    """Create communication poster."""

    success_url = reverse_lazy("com:poster_list")

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        kwargs["app"] = "com"
        return kwargs


class PosterEditView(IsComAdminMixin, ComTabsMixin, PosterEditBaseView):
    """Edit communication poster."""

    success_url = reverse_lazy("com:poster_list")

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        kwargs["app"] = "com"
        return kwargs


class PosterDeleteView(IsComAdminMixin, ComTabsMixin, PosterDeleteBaseView):
    """Delete communication poster."""

    success_url = reverse_lazy("com:poster_list")


class PosterModerateListView(IsComAdminMixin, ComTabsMixin, ListView):
    """Moderate list communication poster."""

    current_tab = "posters"
    model = Poster
    template_name = "com/poster_moderate.jinja"
    queryset = Poster.objects.filter(is_moderated=False).all()

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        kwargs["app"] = "com"
        return kwargs


class PosterModerateView(IsComAdminMixin, ComTabsMixin, View):
    """Moderate communication poster."""

    def get(self, request, *args, **kwargs):
        obj = get_object_or_404(Poster, pk=kwargs["object_id"])
        if obj.can_be_moderated_by(request.user):
            obj.is_moderated = True
            obj.moderator = request.user
            obj.save()
            return redirect("com:poster_moderate_list")
        raise PermissionDenied

    def get_context_data(self, **kwargs):
        kwargs = super(PosterModerateListView, self).get_context_data(**kwargs)
        kwargs["app"] = "com"
        return kwargs


class ScreenListView(IsComAdminMixin, ComTabsMixin, ListView):
    """List communication screens."""

    current_tab = "screens"
    model = Screen
    template_name = "com/screen_list.jinja"


class ScreenSlideshowView(DetailView):
    """Slideshow of actives posters."""

    pk_url_kwarg = "screen_id"
    model = Screen
    template_name = "com/screen_slideshow.jinja"

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        kwargs["posters"] = self.object.active_posters()
        return kwargs


class ScreenCreateView(IsComAdminMixin, ComTabsMixin, CreateView):
    """Create communication screen."""

    current_tab = "screens"
    model = Screen
    fields = ["name"]
    template_name = "core/create.jinja"
    success_url = reverse_lazy("com:screen_list")


class ScreenEditView(IsComAdminMixin, ComTabsMixin, UpdateView):
    """Edit communication screen."""

    pk_url_kwarg = "screen_id"
    current_tab = "screens"
    model = Screen
    fields = ["name"]
    template_name = "com/screen_edit.jinja"
    success_url = reverse_lazy("com:screen_list")


class ScreenDeleteView(IsComAdminMixin, ComTabsMixin, DeleteView):
    """Delete communication screen."""

    pk_url_kwarg = "screen_id"
    current_tab = "screens"
    model = Screen
    template_name = "core/delete_confirm.jinja"
    success_url = reverse_lazy("com:screen_list")
