import base64
from decimal import Decimal
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import ListView
from django.views.generic.dates import MonthArchiveView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from matplotlib.figure import Figure

from ihatetobudget.utils.views import InitialDataAsGETOptionsMixin

from .forms import CategoryForm, ExpenseForm
from .models import Category, Expense


@login_required
def index(request):
    return render(request, "sheets/index.html")


class SheetView(LoginRequiredMixin, MonthArchiveView):
    template_name = "sheets/sheet.html"
    queryset = Expense.objects.all()
    date_field = "date"
    allow_future = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["plot_overview"] = self.generate_plot_overview()
        return context

    def generate_plot_overview(self, figsize=(100, 1), guttersize=Decimal(0.5)):
        categories = self.object_list.values("category").order_by("category")
        amount_list = [
            d["category_sum"]
            for d in categories.annotate(category_sum=Sum("amount"))
        ]
        guttersize *= sum(amount_list) / 100
        color_list = [
            d["category__color"]
            for d in categories.distinct().values("category__color")
        ]
        if color_list[0] is None:
            color_list[0] = "#ddd"  #  Arbitrary color for "No category"

        # Generate the figure **without using pyplot**.
        fig = Figure(figsize=figsize)
        ax = fig.subplots()

        left = 0
        for amount, color in zip(amount_list, color_list):
            ax.barh(y=0, width=amount, height=0.1, color=color, left=left)
            left += amount + guttersize

        ax.axis("off")
        ax.set_xlim(0, left - guttersize)

        buffer = BytesIO()
        fig.savefig(buffer, format="png", bbox_inches="tight", pad_inches=0)

        return base64.b64encode(buffer.getbuffer()).decode("ascii")


class ExpenseCreateView(
    LoginRequiredMixin,
    InitialDataAsGETOptionsMixin,
    SuccessMessageMixin,
    CreateView,
):
    template_name = "ihatetobudget/generic/new-edit-form.html"
    form_class = ExpenseForm
    extra_context = {"title": "New Expense"}

    # InitialDataAsGETOptionsMixin
    fields_with_initial_data_as_get_option = [
        (
            "category",
            lambda option_value: Category.objects.get(name=option_value),
        )
    ]

    # SuccessMessageMixin
    success_message = "Expense added!"


class ExpenseUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    template_name = "ihatetobudget/generic/new-edit-form.html"
    model = Expense
    form_class = ExpenseForm
    extra_context = {"title": "Edit Expense"}

    # SuccessMessageMixin
    success_message = "Expense modified!"


class ExpenseDeleteView(LoginRequiredMixin, DeleteView):
    #  XXX: a `template_name` must be defined if we want to delete via GET.
    #  Currently, we delete via POST (no need to render a template, since we
    #  redirect).

    model = Expense
    success_url = reverse_lazy("sheets:index")

    # SuccessMessageMixin
    success_message = "Expense deleted!"

    def delete(self, request, *args, **kwargs):
        #  XXX: SuccessMessageMixin not working with DeleteView
        messages.success(self.request, self.success_message)

        super_redirect = super().delete(request, *args, **kwargs)
        object = self.object
        if self.model.objects.filter(
            date__year=object.date.year, date__month=object.date.month
        ).first():
            #  There's a least one other object with the same year and month
            return redirect(object.get_absolute_url())
        return super_redirect


class ExpenseListView(LoginRequiredMixin, ListView):
    template_name = "sheets/history.html"
    paginate_by = 10
    model = Expense
    ordering = ["-date"]


class CategoryListView(LoginRequiredMixin, ListView):
    template_name = "sheets/categories.html"
    model = Category


class CategoryCreateView(
    LoginRequiredMixin,
    SuccessMessageMixin,
    CreateView,
):
    template_name = "ihatetobudget/generic/new-edit-form.html"
    form_class = CategoryForm
    extra_context = {"title": "New Category"}

    # SuccessMessageMixin
    success_message = "Category added!"


class CategoryUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    template_name = "ihatetobudget/generic/new-edit-form.html"
    model = Category
    form_class = CategoryForm
    extra_context = {"title": "Edit Category"}

    # SuccessMessageMixin
    success_message = "Category modified!"


class CategoryDeleteView(DeleteView):
    template_name = "ihatetobudget/generic/delete-form.html"
    model = Category
    extra_context = {"title": "Delete Category"}
    success_url = reverse_lazy("sheets:categories")

    # SuccessMessageMixin
    success_message = "Category deleted!"

    def delete(self, request, *args, **kwargs):
        #  XXX: SuccessMessageMixin not working with DeleteView
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)
