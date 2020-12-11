from rest_framework import serializers
from .models import Room


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ('id', 'code', 'host', 'guest_can_pause',
                  'votes_to_skip', 'created_at')


class CreateRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ('guest_can_pause', 'votes_to_skip')


class UpdateRoomSerializer(serializers.ModelSerializer):
    # When we update the serializer will check in the model if the code doesn't exists yet, and then update.
    # But if we are updating a room the code we passed is used by the room itself.
    # So we redefine the code field in serializer, not to reference the one in the Room model
    code = serializers.CharField(validators=[])

    class Meta:
        model = Room
        fields = ('code', 'guest_can_pause', 'votes_to_skip')

    
