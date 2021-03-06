import os
from django.conf import settings
from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.views.generic.edit import FormView
from django.contrib import messages
from .auth_superuser import LoginSuperUserRequiredMixin
from .forms import UploadFileForm
from .utils import in_memory_file_to_temp
from .scraper import data_scraper, data_scraper_two
from .tasks.excel_scraper import excel_parser_task


class DocumentView(FormView, LoginSuperUserRequiredMixin):
    form_class = UploadFileForm
    template_name = 'document.html'
    success_url = 'document'
    success_message = 'File Uploaded successfully updated!!!!'

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        if form.is_valid():
            # filepath = os.path.join(
            #     settings.MEDIA_ROOT, in_memory_file_to_temp(form.cleaned_data.get('file'))
            # )
            messages.error(self.request, self.success_message)
            doc_obj = form.save()
            data_scraper(doc_obj)
            # data_scraper_two(doc_obj.file.name)
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class DocumentExcelView(TemplateView, LoginSuperUserRequiredMixin):
    form_class = UploadFileForm
    template_name = 'excel_documents.html'
    success_url = 'document_excel'
    success_message = 'File Uploaded successfully updated!!!!'

    def get_context_data(self, **kwargs):
        kwargs['form'] = self.form_class()
        return kwargs

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)
        if form.is_valid():
            messages.error(self.request, self.success_message)
            doc_obj = form.save()
            excel_parser_task.delay(doc_obj.id)
            return redirect(self.success_url)
        else:
            return render(request, self.template_name, {'form': form})
