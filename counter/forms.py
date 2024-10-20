from django import forms
from django.utils.translation import gettext_lazy as _
from phonenumber_field.widgets import RegionalPhoneNumberWidget

from club.widgets.select import AutoCompleteSelectClub
from core.views.forms import NFCTextInput, SelectDate, SelectDateTime
from core.views.widgets.select import (
    AutoCompleteSelect,
    AutoCompleteSelectMultipleGroup,
    AutoCompleteSelectMultipleUser,
    AutoCompleteSelectUser,
)
from counter.models import (
    BillingInfo,
    Counter,
    Customer,
    Eticket,
    Product,
    Refilling,
    StudentCard,
)
from counter.widgets.select import (
    AutoCompleteSelectMultipleCounter,
    AutoCompleteSelectMultipleProduct,
    AutoCompleteSelectProduct,
)


class BillingInfoForm(forms.ModelForm):
    class Meta:
        model = BillingInfo
        fields = [
            "first_name",
            "last_name",
            "address_1",
            "address_2",
            "zip_code",
            "city",
            "country",
            "phone_number",
        ]
        widgets = {
            "phone_number": RegionalPhoneNumberWidget,
        }


class StudentCardForm(forms.ModelForm):
    """Form for adding student cards
    Only used for user profile since CounterClick is to complicated.
    """

    class Meta:
        model = StudentCard
        fields = ["uid"]
        widgets = {
            "uid": NFCTextInput,
        }

    def clean(self):
        cleaned_data = super().clean()
        uid = cleaned_data.get("uid", None)
        if not uid or not StudentCard.is_valid(uid):
            raise forms.ValidationError(_("This UID is invalid"), code="invalid")
        return cleaned_data


class GetUserForm(forms.Form):
    """The Form class aims at providing a valid user_id field in its cleaned data, in order to pass it to some view,
    reverse function, or any other use.

    The Form implements a nice JS widget allowing the user to type a customer account id, or search the database with
    some nickname, first name, or last name (TODO)
    """

    code = forms.CharField(
        label="Code",
        max_length=StudentCard.UID_SIZE,
        required=False,
        widget=NFCTextInput,
    )
    id = forms.CharField(
        label=_("Select user"),
        help_text=None,
        widget=AutoCompleteSelectUser,
        required=False,
    )

    def as_p(self):
        self.fields["code"].widget.attrs["autofocus"] = True
        return super().as_p()

    def clean(self):
        cleaned_data = super().clean()
        cus = None
        if cleaned_data["code"] != "":
            if len(cleaned_data["code"]) == StudentCard.UID_SIZE:
                card = StudentCard.objects.filter(uid=cleaned_data["code"])
                if card.exists():
                    cus = card.first().customer
            if cus is None:
                cus = Customer.objects.filter(
                    account_id__iexact=cleaned_data["code"]
                ).first()
        elif cleaned_data["id"] is not None:
            cus = Customer.objects.filter(user=cleaned_data["id"]).first()
        if cus is None or not cus.can_buy:
            raise forms.ValidationError(_("User not found"))
        cleaned_data["user_id"] = cus.user.id
        cleaned_data["user"] = cus.user
        return cleaned_data


class NFCCardForm(forms.Form):
    student_card_uid = forms.CharField(
        max_length=StudentCard.UID_SIZE,
        required=False,
        widget=NFCTextInput,
    )


class RefillForm(forms.ModelForm):
    error_css_class = "error"
    required_css_class = "required"
    amount = forms.FloatField(
        min_value=0, widget=forms.NumberInput(attrs={"class": "focus"})
    )

    class Meta:
        model = Refilling
        fields = ["amount", "payment_method", "bank"]


class CounterEditForm(forms.ModelForm):
    class Meta:
        model = Counter
        fields = ["sellers", "products"]

        widgets = {
            "sellers": AutoCompleteSelectMultipleUser,
            "products": AutoCompleteSelectMultipleProduct,
        }


class ProductEditForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name",
            "description",
            "product_type",
            "code",
            "parent_product",
            "buying_groups",
            "purchase_price",
            "selling_price",
            "special_selling_price",
            "icon",
            "club",
            "limit_age",
            "tray",
            "archived",
        ]
        widgets = {
            "parent_product": AutoCompleteSelectMultipleProduct,
            "product_type": AutoCompleteSelect,
            "buying_groups": AutoCompleteSelectMultipleGroup,
            "club": AutoCompleteSelectClub,
        }

    counters = forms.ModelMultipleChoiceField(
        help_text=None,
        label=_("Counters"),
        required=False,
        widget=AutoCompleteSelectMultipleCounter,
        queryset=Counter.objects.all(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.id:
            self.fields["counters"].initial = self.instance.counters.all()

    def save(self, *args, **kwargs):
        ret = super().save(*args, **kwargs)
        if self.fields["counters"].initial:
            # Remove the product from all counter it was added to
            # It will then only be added to selected counters
            for counter in self.fields["counters"].initial:
                counter.products.remove(self.instance)
                counter.save()
        for counter in self.cleaned_data["counters"]:
            counter.products.add(self.instance)
            counter.save()
        return ret


class CashSummaryFormBase(forms.Form):
    begin_date = forms.DateTimeField(
        label=_("Begin date"), widget=SelectDateTime, required=False
    )
    end_date = forms.DateTimeField(
        label=_("End date"), widget=SelectDateTime, required=False
    )


class EticketForm(forms.ModelForm):
    class Meta:
        model = Eticket
        fields = ["product", "banner", "event_title", "event_date"]
        widgets = {
            "product": AutoCompleteSelectProduct,
            "event_date": SelectDate,
        }
