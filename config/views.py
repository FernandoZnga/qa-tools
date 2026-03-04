from django.views.generic import TemplateView


class HomeView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'home'
        context['page_title'] = 'QA Tools | Home'
        return context


class FormatterView(TemplateView):
    template_name = 'formatter.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'formatter'
        context['page_title'] = 'QA Tools | Formatter'
        return context


class DiffView(TemplateView):
    template_name = 'diff.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'diff'
        context['page_title'] = 'QA Tools | Diff'
        return context


class ApiToolView(TemplateView):
    template_name = 'api.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'api'
        context['page_title'] = 'QA Tools | API Sender'
        return context


class StressView(TemplateView):
    template_name = 'stress.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'stress'
        context['page_title'] = 'QA Tools | Stress'
        return context


class DataGeneratorView(TemplateView):
    template_name = 'data.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'data'
        context['page_title'] = 'QA Tools | Random Data'
        return context


class AsyncRunsView(TemplateView):
    template_name = 'runs.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'runs'
        context['page_title'] = 'QA Tools | Async Runs'
        return context
