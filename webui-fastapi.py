import os
import logging
import sys

import gradio as gr
import asyncio

from modules import config
from modules.config import *
from modules.utils import *
from modules.presets import *
from modules.overwrites import *
from modules.models.models import get_model


import threading
import time
import json
import random
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
import json
from typing import List
import os
import random
import time
import asyncio
from starlette.middleware.cors import CORSMiddleware

import logging
import uvicorn

import g4f
from g4f import Model, ChatCompletion, Provider

logging.getLogger("httpx").setLevel(logging.WARNING)

gr.Chatbot._postprocess_chat_messages = postprocess_chat_messages
gr.Chatbot.postprocess = postprocess

with open("assets/custom.css", "r", encoding="utf-8") as f:
    customCSS = f.read()

def create_new_model():
    return get_model(model_name=MODELS[DEFAULT_MODEL], access_key=my_api_key)[0]

with gr.Blocks(css=customCSS, theme=small_and_beautiful_theme) as demo:
    user_name = gr.State("")
    promptTemplates = gr.State(load_template(get_template_names(plain=True)[0], mode=2))
    user_question = gr.State("")
    assert type(my_api_key) == str
    user_api_key = gr.State(my_api_key)
    current_model = gr.State(create_new_model)

    topic = gr.State("История неименованного диалога")

    with gr.Row():
        gr.HTML(CHUANHU_TITLE, elem_id="app_title")
        status_display = gr.Markdown(get_geoip(), elem_id="status_display")
    with gr.Row(elem_id="float_display"):
        user_info = gr.Markdown(value="getting user info...", elem_id="user_info")
        update_info = gr.HTML(get_html("update.html").format(
            current_version=repo_html(),
            version_time=version_time(),
            cancel_btn="Отмена",
            update_btn="Обновить",
            seenew_btn="Подробности",
            ok_btn="OK",
        ), visible=check_update)

    with gr.Row(equal_height=True):
        with gr.Column(scale=5):
            with gr.Row():
                chatbot = gr.Chatbot(label="Chuanhu Chat", elem_id="chuanhu_chatbot", latex_delimiters=latex_delimiters_set, height=700)
            with gr.Row():
                with gr.Column(min_width=225, scale=12):
                    user_input = gr.Textbox(
                        elem_id="user_input_tb",
                        show_label=False, placeholder="Введите ваш запроос здесь",
                        container=False
                    )
                with gr.Column(min_width=42, scale=1):
                    submitBtn = gr.Button(value="", variant="primary", elem_id="submit_btn")
                    cancelBtn = gr.Button(value="", variant="secondary", visible=False, elem_id="cancel_btn")
            with gr.Row():
                emptyBtn = gr.Button(
                    "🧹 Новый диалог", elem_id="empty_btn"
                )
                retryBtn = gr.Button("🔄 Перегенерировать")
                delFirstBtn = gr.Button("🗑️ Удалить самый старый диалог")
                delLastBtn = gr.Button("🗑️ Удалить последний диалог")
                with gr.Row(visible=False) as like_dislike_area:
                    with gr.Column(min_width=20, scale=1):
                        likeBtn = gr.Button("👍")
                    with gr.Column(min_width=20, scale=1):
                        dislikeBtn = gr.Button("👎")

        with gr.Column():
            with gr.Column(min_width=50, scale=1):
                with gr.Tab(label="Модель"):
                    keyTxt = gr.Textbox(
                        show_label=True,
                        placeholder="Your API-key...",
                        value=hide_middle_chars(user_api_key.value),
                        type="password",
                        visible=not HIDE_MY_KEY,
                        label="API-Key",
                    )
                    if multi_api_key:
                        usageTxt = gr.Markdown("Многопользовательский режим включен, не нужно вводить ключ, можно сразу начать диалог", elem_id="usage_display", elem_classes="insert_block")
                    else:
                        usageTxt = gr.Markdown("**Отправьте сообщение** или **Отправьте ключ** для отображения кредита", elem_id="usage_display", elem_classes="insert_block")
                    model_select_dropdown = gr.Dropdown(
                        label="Выберите модель", choices=MODELS, multiselect=False, value=MODELS[DEFAULT_MODEL], interactive=True
                    )
                    lora_select_dropdown = gr.Dropdown(
                        label="Выберите модель LoRA", choices=[], multiselect=False, interactive=True, visible=False
                    )
                    with gr.Row():
                        single_turn_checkbox = gr.Checkbox(label="Single-turn режим диалога", value=False, elem_classes="switch_checkbox")
                        use_websearch_checkbox = gr.Checkbox(label="Использовать онлайн-поиск", value=False, elem_classes="switch_checkbox")

                    language_select_dropdown = gr.Dropdown(
                        label="Выберите язык ответа (для функций поиска и индексации)",
                        choices=REPLY_LANGUAGES,
                        multiselect=False,
                        value=REPLY_LANGUAGES[0],
                    )
                    index_files = gr.Files(label="Загрузить (ChimeraAPI)", type="file")
                    two_column = gr.Checkbox(label="Двухстолбчатый pdf", value=advance_docs["pdf"].get("two_column", False))
                    summarize_btn = gr.Button("Резюмировать")
                    # TODO: OCR формулы
                    # formula_ocr = gr.Checkbox(label="OCR формулы", value=advance_docs["pdf"].get("formula_ocr", False))

                with gr.Tab(label="Prompt"):
                    systemPromptTxt = gr.Textbox(
                        show_label=True,
                        placeholder="Введите здесь System Prompt...",
                        label="System prompt",
                        value=INITIAL_SYSTEM_PROMPT,
                        lines=10
                    )
                    with gr.Accordion(label="Загрузить шаблон Prompt", open=True):
                        with gr.Column():
                            with gr.Row():
                                with gr.Column(scale=6):
                                    templateFileSelectDropdown = gr.Dropdown(
                                        label="Выберите файл с коллекцией шаблонов Prompt",
                                        choices=get_template_names(plain=True),
                                        multiselect=False,
                                        value=get_template_names(plain=True)[0],
                                        container=False,
                                    )
                                with gr.Column(scale=1):
                                    templateRefreshBtn = gr.Button("🔄 Обновить")
                            with gr.Row():
                                with gr.Column():
                                    templateSelectDropdown = gr.Dropdown(
                                        label="Загрузить из шаблона Prompt",
                                        choices=load_template(
                                            get_template_names(plain=True)[0], mode=1
                                        ),
                                        multiselect=False,
                                        container=False,
                                    )

                with gr.Tab(label="Сохранить/Загрузить"):
                    with gr.Accordion(label="Сохранить/Загрузить историю диалога", open=True):
                        with gr.Column():
                            with gr.Row():
                                with gr.Column(scale=6):
                                    historyFileSelectDropdown = gr.Dropdown(
                                        label="Загрузить диалог из списка",
                                        choices=get_history_names(plain=True),
                                        multiselect=False,
                                        container=False,
                                    )
                                with gr.Row():
                                    with gr.Column(min_width=42, scale=1):
                                        historyRefreshBtn = gr.Button("🔄 Обновить")
                                    with gr.Column(min_width=42, scale=1):
                                        historyDeleteBtn = gr.Button("🗑️ Удалить")
                            with gr.Row():
                                with gr.Column(scale=6):
                                    saveFileName = gr.Textbox(
                                        show_label=True,
                                        placeholder="Установить имя файла: по умолчанию .json, можно выбрать .md",
                                        label="Выберите имя файла для сохранения",
                                        value="История диалога",
                                        container=False,
                                    )
                                with gr.Column(scale=1):
                                    saveHistoryBtn = gr.Button("💾 Сохранить диалог")
                                    exportMarkdownBtn = gr.Button("📝 Экспортировать в Markdown")
                                    gr.Markdown("По умолчанию сохраняется в папке истории")
                            with gr.Row():
                                with gr.Column():
                                    downloadFile = gr.File(interactive=True)

                with gr.Tab(label="Расширенный"):
                    gr.HTML(get_html("appearance_switcher.html").format(label="Переключить светлую/темную тему"), elem_classes="insert_block")
                    use_streaming_checkbox = gr.Checkbox(
                            label="Стриминг текста", value=True, visible=ENABLE_STREAMING_OPTION, elem_classes="switch_checkbox"
                        )
                    checkUpdateBtn = gr.Button("🔄 Проверить обновления...", visible=check_update)
                    gr.Markdown("# ⚠️ ОСТОРОЖНО ⚠️", elem_id="advanced_warning")
                    with gr.Accordion("Параметры", open=False):
                        temperature_slider = gr.Slider(
                            minimum=-0,
                            maximum=2.0,
                            value=1.0,
                            step=0.1,
                            interactive=True,
                            label="temperature",
                        )
                        top_p_slider = gr.Slider(
                            minimum=-0,
                            maximum=1.0,
                            value=1.0,
                            step=0.05,
                            interactive=True,
                            label="top-p",
                        )
                        n_choices_slider = gr.Slider(
                            minimum=1,
                            maximum=10,
                            value=1,
                            step=1,
                            interactive=True,
                            label="n choices",
                        )
                        stop_sequence_txt = gr.Textbox(
                            show_label=True,
                            placeholder="Введите здесь стоп-слова, разделенные запятой...",
                            label="stop",
                            value="",
                            lines=1,
                        )
                        max_context_length_slider = gr.Slider(
                            minimum=1,
                            maximum=32768,
                            value=4000,
                            step=1,
                            interactive=True,
                            label="max context",
                        )
                        max_generation_slider = gr.Slider(
                            minimum=1,
                            maximum=32768,
                            value=2000,
                            step=1,
                            interactive=True,
                            label="max generations",
                        )
                        presence_penalty_slider = gr.Slider(
                            minimum=-2.0,
                            maximum=2.0,
                            value=0.0,
                            step=0.01,
                            interactive=True,
                            label="presence penalty",
                        )
                        frequency_penalty_slider = gr.Slider(
                            minimum=-2.0,
                            maximum=2.0,
                            value=0.0,
                            step=0.01,
                            interactive=True,
                            label="frequency penalty",
                        )
                        logit_bias_txt = gr.Textbox(
                            show_label=True,
                            placeholder="word:likelihood",
                            label="logit bias",
                            value="",
                            lines=1,
                        )
                        user_identifier_txt = gr.Textbox(
                            show_label=True,
                            placeholder="Используется для локализации злоупотреблений",
                            label="Имя пользователя",
                            value=user_name.value,
                            lines=1,
                        )

                    with gr.Accordion("Сетевые настройки", open=False):
                        # 优先展示自定义的api_host
                        apihostTxt = gr.Textbox(
                            show_label=True,
                            placeholder="Введите здесь API-Host...",
                            label="API-Host",
                            value=config.api_host or shared.API_HOST,
                            lines=1,
                            container=False,
                        )
                        changeAPIURLBtn = gr.Button("🔄 Переключить API-адрес")
                        proxyTxt = gr.Textbox(
                            show_label=True,
                            placeholder="Введите здесь адрес прокси...",
                            label="Адрес прокси (например: http://127.0.0.1:10809）",
                            value="",
                            lines=2,
                            container=False,
                        )
                        changeProxyBtn = gr.Button("🔄 Установить адрес прокси")
                        default_btn = gr.Button("🔙 Восстановить настройки по умолчанию")

    gr.Markdown(CHUANHU_DESCRIPTION, elem_id="description")
    gr.HTML(get_html("footer.html").format(versions=versions_html()), elem_id="footer")

    # https://github.com/gradio-app/gradio/pull/3296
    def create_greeting(request: gr.Request):
        if hasattr(request, "username") and request.username: # is not None or is not ""
            logging.info(f"Get User Name: {request.username}")
            user_info, user_name = gr.Markdown.update(value=f"User: {request.username}"), request.username
        else:
            user_info, user_name = gr.Markdown.update(value=f"", visible=False), ""
        current_model = get_model(model_name=MODELS[DEFAULT_MODEL], access_key=my_api_key)[0]
        current_model.set_user_identifier(user_name)
        chatbot = gr.Chatbot.update(label=MODELS[DEFAULT_MODEL])
        return user_info, user_name, current_model, toggle_like_btn_visibility(DEFAULT_MODEL), *current_model.auto_load(), get_history_names(False, user_name), chatbot
    demo.load(create_greeting, inputs=None, outputs=[user_info, user_name, current_model, like_dislike_area, systemPromptTxt, chatbot, historyFileSelectDropdown, chatbot], api_name="load")
    chatgpt_predict_args = dict(
        fn=predict,
        inputs=[
            current_model,
            user_question,
            chatbot,
            use_streaming_checkbox,
            use_websearch_checkbox,
            index_files,
            language_select_dropdown,
        ],
        outputs=[chatbot, status_display],
        show_progress=True,
    )

    start_outputing_args = dict(
        fn=start_outputing,
        inputs=[],
        outputs=[submitBtn, cancelBtn],
        show_progress=True,
    )

    end_outputing_args = dict(
        fn=end_outputing, inputs=[], outputs=[submitBtn, cancelBtn]
    )

    reset_textbox_args = dict(
        fn=reset_textbox, inputs=[], outputs=[user_input]
    )

    transfer_input_args = dict(
        fn=transfer_input, inputs=[user_input], outputs=[user_question, user_input, submitBtn, cancelBtn], show_progress=True
    )

    get_usage_args = dict(
        fn=billing_info, inputs=[current_model], outputs=[usageTxt], show_progress=False
    )

    load_history_from_file_args = dict(
        fn=load_chat_history,
        inputs=[current_model, historyFileSelectDropdown, user_name],
        outputs=[saveFileName, systemPromptTxt, chatbot]
    )

    refresh_history_args = dict(
        fn=get_history_names, inputs=[gr.State(False), user_name], outputs=[historyFileSelectDropdown]
    )


    # Chatbot
    cancelBtn.click(interrupt, [current_model], [])

    user_input.submit(**transfer_input_args).then(**chatgpt_predict_args).then(**end_outputing_args)
    user_input.submit(**get_usage_args)

    submitBtn.click(**transfer_input_args).then(**chatgpt_predict_args, api_name="predict").then(**end_outputing_args)
    submitBtn.click(**get_usage_args)

    index_files.change(handle_file_upload, [current_model, index_files, chatbot, language_select_dropdown], [index_files, chatbot, status_display])
    summarize_btn.click(handle_summarize_index, [current_model, index_files, chatbot, language_select_dropdown], [chatbot, status_display])

    emptyBtn.click(
        reset,
        inputs=[current_model],
        outputs=[chatbot, status_display],
        show_progress=True,
        _js='()=>{clearHistoryHtml();}',
    )

    retryBtn.click(**start_outputing_args).then(
        retry,
        [
            current_model,
            chatbot,
            use_streaming_checkbox,
            use_websearch_checkbox,
            index_files,
            language_select_dropdown,
        ],
        [chatbot, status_display],
        show_progress=True,
    ).then(**end_outputing_args)
    retryBtn.click(**get_usage_args)

    delFirstBtn.click(
        delete_first_conversation,
        [current_model],
        [status_display],
    )

    delLastBtn.click(
        delete_last_conversation,
        [current_model, chatbot],
        [chatbot, status_display],
        show_progress=False
    )

    likeBtn.click(
        like,
        [current_model],
        [status_display],
        show_progress=False
    )

    dislikeBtn.click(
        dislike,
        [current_model],
        [status_display],
        show_progress=False
    )

    two_column.change(update_doc_config, [two_column], None)

    # LLM Models
    keyTxt.change(set_key, [current_model, keyTxt], [user_api_key, status_display], api_name="set_key").then(**get_usage_args)
    keyTxt.submit(**get_usage_args)
    single_turn_checkbox.change(set_single_turn, [current_model, single_turn_checkbox], None)
    model_select_dropdown.change(get_model, [model_select_dropdown, lora_select_dropdown, user_api_key, temperature_slider, top_p_slider, systemPromptTxt, user_name], [current_model, status_display, chatbot, lora_select_dropdown], show_progress=True, api_name="get_model")
    model_select_dropdown.change(toggle_like_btn_visibility, [model_select_dropdown], [like_dislike_area], show_progress=False)
    lora_select_dropdown.change(get_model, [model_select_dropdown, lora_select_dropdown, user_api_key, temperature_slider, top_p_slider, systemPromptTxt, user_name], [current_model, status_display, chatbot], show_progress=True)

    # Template
    systemPromptTxt.change(set_system_prompt, [current_model, systemPromptTxt], None)
    templateRefreshBtn.click(get_template_names, None, [templateFileSelectDropdown])
    templateFileSelectDropdown.change(
        load_template,
        [templateFileSelectDropdown],
        [promptTemplates, templateSelectDropdown],
        show_progress=True,
    )
    templateSelectDropdown.change(
        get_template_content,
        [promptTemplates, templateSelectDropdown, systemPromptTxt],
        [systemPromptTxt],
        show_progress=True,
    )

    # S&L
    saveHistoryBtn.click(
        save_chat_history,
        [current_model, saveFileName, chatbot, user_name],
        downloadFile,
        show_progress=True,
    )
    saveHistoryBtn.click(get_history_names, [gr.State(False), user_name], [historyFileSelectDropdown])
    exportMarkdownBtn.click(
        export_markdown,
        [current_model, saveFileName, chatbot, user_name],
        downloadFile,
        show_progress=True,
    )
    historyRefreshBtn.click(**refresh_history_args)
    historyDeleteBtn.click(delete_chat_history, [current_model, historyFileSelectDropdown, user_name], [status_display, historyFileSelectDropdown, chatbot], _js='(a,b,c)=>{return showConfirmationDialog(a, b, c);}')
    historyFileSelectDropdown.change(**load_history_from_file_args)
    downloadFile.change(upload_chat_history, [current_model, downloadFile, user_name], [saveFileName, systemPromptTxt, chatbot])

    # Advanced
    max_context_length_slider.change(set_token_upper_limit, [current_model, max_context_length_slider], None)
    temperature_slider.change(set_temperature, [current_model, temperature_slider], None)
    top_p_slider.change(set_top_p, [current_model, top_p_slider], None)
    n_choices_slider.change(set_n_choices, [current_model, n_choices_slider], None)
    stop_sequence_txt.change(set_stop_sequence, [current_model, stop_sequence_txt], None)
    max_generation_slider.change(set_max_tokens, [current_model, max_generation_slider], None)
    presence_penalty_slider.change(set_presence_penalty, [current_model, presence_penalty_slider], None)
    frequency_penalty_slider.change(set_frequency_penalty, [current_model, frequency_penalty_slider], None)
    logit_bias_txt.change(set_logit_bias, [current_model, logit_bias_txt], None)
    user_identifier_txt.change(set_user_identifier, [current_model, user_identifier_txt], None)

    default_btn.click(
        reset_default, [], [apihostTxt, proxyTxt, status_display], show_progress=True
    )
    changeAPIURLBtn.click(
        change_api_host,
        [apihostTxt],
        [status_display],
        show_progress=True,
    )
    changeProxyBtn.click(
        change_proxy,
        [proxyTxt],
        [status_display],
        show_progress=True,
    )
    checkUpdateBtn.click(fn=None, _js='()=>{manualCheckUpdate();}')

logging.info(
    colorama.Back.GREEN
    + "\n川虎的温馨提示：访问 http://localhost:7860 查看界面"
    + colorama.Style.RESET_ALL
)
# 默认开启本地服务器，默认可以直接从IP访问，默认不创建公开分享链接
demo.title = "川虎Chat 🚀"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/chat/completions")
@app.post("/v1/chat/completions")
@app.post("/")
async def chat_completions(request: Request):
    req_data = await request.json()
    streaming = req_data.get('stream', False)
    req_data = await request.json()
    streaming = req_data.get('stream', False)
    streaming_ = req_data.json.get('stream', False)
    model = req_data.json['model']
    messages = req_data.json.get('messages')
    provider = req_data.json.get('provider', False)
    if provider == 'Chimera':
        response = g4f.ChatCompletion.create(model='gpt-4', provider=g4f.Provider.Chimera, stream=streaming,
                                             messages=messages)
    else:
        if not provider:
            r = requests.get('https://provider.neurochat-gpt.ru/v1/status')
            data = r.json()['data']
            random.shuffle(data)
            for provider_info in data:
                for model_info in provider_info['model']:
                    if model in model_info and model_info[model]['status'] == 'Active':
                        if getattr(g4f.Provider,provider_info['provider']).supports_stream != streaming_:
                          streaming = False
                        else:
                          streaming = True
                        response = g4f.ChatCompletion.create(model=model, provider=getattr(g4f.Provider,provider_info['provider']),stream=streaming,
                                         messages=messages)
                        provider_name = provider_info['provider']
                        print(provider_name)
                        break
                else:
                    continue
                break
        else:
            provider_name = provider
            if getattr(g4f.Provider,provider).supports_stream != streaming_:
              streaming = False
            else:
              streaming = True
            response = g4f.ChatCompletion.create(model=model, provider=getattr(g4f.Provider,provider),stream=streaming,
                                         messages=messages)
    if not provider:
      while 'curl_cffi.requests.errors.RequestsError' in response:
          random.shuffle(data)
          for provider_info in data:
              for model_info in provider_info['model']:
                  if model in model_info and model_info[model]['status'] == 'Active':
                      if getattr(g4f.Provider,provider_info['provider']).supports_stream != streaming_:
                        streaming = False
                      else:
                        streaming = True
                      response = g4f.ChatCompletion.create(model=model, provider=getattr(g4f.Provider,provider_info['provider']),stream=streaming,
                                      messages=messages)
                      provider_name = provider_info['provider']
                      print(provider_name)
                      break
              else:
                  continue
              break
                
    if not streaming_:
        completion_timestamp = int(time.time())
        completion_id = ''.join(random.choices(
            'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789', k=28))

        return {
            'id': 'chatcmpl-%s' % completion_id,
            'object': 'chat.completion',
            'created': completion_timestamp,
            'model': model,
            'provider':provider_name,
            'supports_stream':getattr(g4f.Provider,provider_name).supports_stream,
            'usage': {
                'prompt_tokens': len(messages),
                'completion_tokens': len(response),
                'total_tokens': len(messages)+len(response)
            },
            'choices': [{
                'message': {
                    'role': 'assistant',
                    'content': response
                },
                'finish_reason': 'stop',
                'index': 0
            }]
        }
    #print(response)
    def stream():
        nonlocal response
        for token in response:
            completion_timestamp = int(time.time())
            completion_id = ''.join(random.choices(
                'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789', k=28))

            completion_data = {
                'id': f'chatcmpl-{completion_id}',
                'object': 'chat.completion.chunk',
                'created': completion_timestamp,
                'choices': [
                    {
                        'delta': {
                            'content': token
                        },
                        'index': 0,
                        'finish_reason': None
                    }
                ]
            }
            #print(token)
            #print(completion_data)
            #print('data: %s\n\n' % json.dumps(completion_data, separators=(',' ':')))
            yield 'data: %s\n\n' % json.dumps(completion_data, separators=(',' ':'))
            time.sleep(0.01)
    print('===Start Streaming===')
    return app.response_class(stream(), mimetype='text/event-stream')

@app.get("/v1/dashboard/billing/subscription")
@app.get("/dashboard/billing/subscription")
async def billing_subscription():
    return JSONResponse({
  "object": "billing_subscription",
  "has_payment_method": True,
  "canceled": False,
  "canceled_at": None,
  "delinquent": None,
  "access_until": 2556028800,
  "soft_limit": 6944500,
  "hard_limit": 166666666,
  "system_hard_limit": 166666666,
  "soft_limit_usd": 416.67,
  "hard_limit_usd": 9999.99996,
  "system_hard_limit_usd": 9999.99996,
  "plan": {
    "title": "Pay-as-you-go",
    "id": "payg"
  },
  "primary": True,
  "account_name": "OpenAI",
  "po_number": None,
  "billing_email": None,
  "tax_ids": None,
  "billing_address": {
    "city": "New York",
    "line1": "OpenAI",
    "country": "US",
    "postal_code": "NY10031"
  },
  "business_address": None
}
)


@app.get("/v1/dashboard/billing/usage")
@app.get("/dashboard/billing/usage")
async def billing_usage():
    return JSONResponse({
  "object": "list",
  "daily_costs": [
    {
      "timestamp": time.time(),
      "line_items": [
        {
          "name": "GPT-4",
          "cost": 0.0
        },
        {
          "name": "Chat models",
          "cost": 1.01
        },
        {
          "name": "InstructGPT",
          "cost": 0.0
        },
        {
          "name": "Fine-tuning models",
          "cost": 0.0
        },
        {
          "name": "Embedding models",
          "cost": 0.0
        },
        {
          "name": "Image models",
          "cost": 16.0
        },
        {
          "name": "Audio models",
          "cost": 0.0
        }
      ]
    }
  ],
  "total_usage": 1.01
}
)

@app.get("/v1/models")
@app.get("/models")
async def models():
  import g4f.models
  model = {"data":[]}
  for i in g4f.models.ModelUtils.convert:
    model['data'].append({
            "id": i,
            "object": "model",
            "owned_by": g4f.models.ModelUtils.convert[i].base_provider,
            "tokens": 99999,
            "fallbacks": None,
            "endpoints": [
                "/v1/chat/completions"
            ],
            "limits": None,
            "permission": []
        })
  return JSONResponse(model)

@app.get("/v1/providers")
@app.get("/providers")
async def providers():
  files = os.listdir("g4f/Provider/Providers")
  files = [f for f in files if os.path.isfile(os.path.join("g4f/Provider/Providers", f))]
  files.sort(key=str.lower)
  providers_data = {"data":[]}
  for file in files:
      if file.endswith(".py"):
          name = file[:-3]
          try:
              p = getattr(g4f.Provider,name)
              providers_data["data"].append({
              "provider": str(name),
              "model": list(p.model),
              "url": str(p.url),
              "working": bool(p.working),
              "supports_stream": bool(p.supports_stream)
              })
          except:
                pass
  return JSONResponse(providers_data)


def setup_logging():
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    root_logger.addHandler(handler)


if __name__ == "__main__":
    setup_logging()
    uvicorn.run("webui-fastapi:app", host="0.0.0.0", port=5000, log_level="info", lifespan='on')