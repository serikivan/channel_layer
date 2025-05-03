import random
import time

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import json
from channel.utils import (text_to_bits, bits_to_text,
                    encode_bitstring, decode_bitstring,
                    make_mistake, LOSS_PROBABILITY)

@swagger_auto_schema(
    method='post',
    operation_id="processSegment",
    operation_description="Обработка сегмента от транспортного уровня",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['sender', 'messageId', 'segmentIndex', 'totalSegments', 'payload'],
        properties={
            'sender': openapi.Schema(type=openapi.TYPE_STRING, description='Отправитель', example='earth-station'),
            'messageId': openapi.Schema(type=openapi.TYPE_STRING, description='ID сообщения', example='msg-001'),
            'segmentIndex': openapi.Schema(type=openapi.TYPE_INTEGER, description='Индекс сегмента', example=0),
            'totalSegments': openapi.Schema(type=openapi.TYPE_INTEGER, description='Всего сегментов', example=5),
            'payload': openapi.Schema(type=openapi.TYPE_STRING, description='Полезная нагрузка', example='Hello segment 0'),
        },
    ),
    responses={
        200: openapi.Response(description="Сегмент обработки", schema=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'sender': openapi.Schema(type=openapi.TYPE_STRING),
                'messageId': openapi.Schema(type=openapi.TYPE_STRING),
                'segmentIndex': openapi.Schema(type=openapi.TYPE_INTEGER),
                'totalSegments': openapi.Schema(type=openapi.TYPE_INTEGER),
                'payload': openapi.Schema(type=openapi.TYPE_STRING),
                'segment_lost': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                'original_bit_length': openapi.Schema(type=openapi.TYPE_INTEGER),
                'restored_bit_length': openapi.Schema(type=openapi.TYPE_INTEGER),
            }
        )),
        204: openapi.Response(description="Сегмент потерян"),
        400: "Ошибка клиента",
        500: "Ошибка сервера"
    }
)
@api_view(['POST'])
def process_segment(request):
    time.sleep(2)
    try:
        original_data = {
            "sender": request.data.get('sender', ''),
            "messageId": request.data.get('messageId', ''),
            "segmentIndex": request.data.get('segmentIndex', 0),
            "totalSegments": request.data.get('totalSegments', 0),
            "payload": request.data.get('payload', '')
        }

        if any(v in [None, ''] for v in original_data.values()):
            return Response({"error": "All fields are required"}, status=status.HTTP_400_BAD_REQUEST)

        # Возможная потеря сегмента
        if random.random() < LOSS_PROBABILITY:
            return Response({"message": "Segment lost on channel"}, status=status.HTTP_204_NO_CONTENT)

        # Все поля в JSON-строку
        combined_data = json.dumps(original_data, ensure_ascii=False)

        print(combined_data)

        # Перевод JSON-строки в битовую строку
        bits = text_to_bits(combined_data)
        original_bit_length = len(bits)  # Сохраняем оригинальную длину

        print(bits)

        # Дополнение битовой строки до длины, кратной 4
        padding_length = (4 - (len(bits) % 4)) % 4
        padded_bits = bits + '0' * padding_length

        # Кодирование 4-битных групп циклическим кодом (7,4)
        encoded = ''
        for i in range(0, len(padded_bits), 4):
            chunk = padded_bits[i:i + 4]
            encoded += encode_bitstring(chunk)

        # Внесение ошибки
        corrupted = make_mistake(encoded)

        # Декодирование по 7-битным группам
        decoded_bits = ''
        for i in range(0, len(corrupted), 7):
            codeword = corrupted[i:i + 7]
            if len(codeword) == 7:
                decoded_bits += decode_bitstring(codeword)

        # Обрезаем добавленные нули и лишние биты
        decoded_bits = decoded_bits[:original_bit_length]

        # Перевод битов в JSON-строку
        restored_json = bits_to_text(decoded_bits)

        print(restored_json)
        restored_data = json.loads(restored_json)

        return Response({
            "sender": restored_data.get("sender", ""),
            "messageId": restored_data.get("messageId", ""),
            "segmentIndex": restored_data.get("segmentIndex", 0),
            "totalSegments": restored_data.get("totalSegments", 0),
            "payload": restored_data.get("payload", ""),
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(
    method='post',
    operation_id="processAck",
    operation_description="Обработка ACK без изменений.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=[],
        properties={
            'messageId': openapi.Schema(type=openapi.TYPE_STRING, description='ID сообщения', example='msg-001'),
            'lastConfirmedSegment': openapi.Schema(type=openapi.TYPE_INTEGER,
                                                   description='Последний полученный сегмент', example=0),
        },
    ),
    responses={
        200: openapi.Response(description="ACK получен"),
        204: openapi.Response(description="ACK потерян"),
    }
)
@api_view(['POST'])
def process_ack(request):

    time.sleep(2)

    if random.random() < LOSS_PROBABILITY:
        return Response({"message": "Segment lost on channel"}, status=status.HTTP_204_NO_CONTENT)


    ack = request.data
    return Response(ack, status=status.HTTP_200_OK)
