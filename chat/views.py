import re

from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from accounts.auth_middleware import LoginProfileRequiredMixin
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.http import JsonResponse
from chat.models import Conversation, ConversationContent, Bot
from .bot import get_bot_response, get_bot_response_gptj, get_bot_answers
from .bot import BotManagement
from .forms import ConversationForm
from django.urls import reverse


class ChatView(LoginProfileRequiredMixin, TemplateView):
    template_name = 'chat.html'


class GetChatListView(LoginProfileRequiredMixin, TemplateView):
    template_name = 'tabs/chat/bot_chat_tab_list.html'
    model = Conversation

    def get(self, request, *args, **kwargs):
        chats = self.model.objects.all().order_by('-created_at')
        context = {'chats': chats}
        data = dict()
        data['html_chat_list'] = render_to_string(self.template_name, context, request=request)
        active_chat = chats.first()
        data['id'] = active_chat.id
        data['chat_id'] = 'chat_' + str(active_chat.id)
        data['url'] = reverse('get_chat_content', kwargs={'pk': active_chat.id})
        return JsonResponse(data)


class GetChatContentView(LoginProfileRequiredMixin, TemplateView):
    template_name = 'content/chat/bot_chat_content_async.html'
    model = ConversationContent

    def get(self, request, *args, **kwargs):
        chats = ConversationContent.objects.filter(conversation__id=kwargs['pk'])
        context = {'chats': chats}
        data = dict()
        data['html_chat_content'] = render_to_string(self.template_name, context, request=request)
        return JsonResponse(data)


class CreateConversationView(LoginProfileRequiredMixin, TemplateView):
    template_name = 'forms/create_new_conversation.html'
    model = ConversationContent
    form = ConversationForm

    def get(self, request, *args, **kwargs):
        form = self.form(initial={'user': request.user})
        context = {'form': form}
        data = dict()
        data['html_new_chat_form'] = render_to_string(self.template_name, context, request=request)
        return JsonResponse(data)

    def post(self, request, *args, **kwargs):
        data = dict()
        # import pdb;pdb.set_trace()
        form = self.form(request.POST)
        form.instance.user = self.request.user.profile
        if form.is_valid():
            form.save()
            data['form_is_valid'] = True
        else:
            data['form_is_valid'] = False
            context = {'form': form}
            data['html_new_chat_form'] = render_to_string(self.template_name, context, request=request)
        return JsonResponse(data)


class SendMessageView(LoginProfileRequiredMixin, TemplateView):
    template_name = 'content/chat/bot_send_messsage_response.html'
    model = ConversationContent

    def post(self, request, *args, **kwargs):
        query = request.POST.get('message')
        conversation = get_object_or_404(Conversation, pk=kwargs['coversation_id'])
        chat = ConversationContent(conversation=conversation, query=query,
                                   sender=request.user.profile)
        if conversation.bot.api.type == 'gpt_j':
            response = get_bot_response_gptj(conversation.bot, query)
            print(response)
            text_response = response.get('result')[0]
            text_response = re.sub(r"\bendoftext\b", '', text_response)
            text_response = re.sub(r"[<|>?]", '', text_response)
        elif conversation.bot.api.type == 'gpt_3' and conversation.bot.api.subtype == 'q&a':
            response = BotManagement().search_response(query)
            text_response = response.get('choices')[0].get('text')
        elif conversation.bot.api.type == 'gpt_3' and conversation.bot.api.subtype == 'answers':
            response = get_bot_answers(conversation.bot, query, conversation)
            text_response = response.get('answers')[0]
        if response:
            chat.response = text_response
            chat.response_json = response
        chat.save()
        context = {'chat': chat}
        data = dict()
        data['html_chat_response'] = render_to_string(self.template_name, context, request=request)
        return JsonResponse(data)
