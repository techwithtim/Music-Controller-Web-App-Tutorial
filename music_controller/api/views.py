from django.shortcuts import render
from rest_framework import generics, status
from .serializers import RoomSerializer, CreateRoomSerializer, UpdateRoomSerializer
from .models import Room
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import JsonResponse


'''
The views in django are the controllers of the model view controller pattern.
So they are not thought to render the UI, they are meant to explicit the logic of the UI
Templates are meant to render the view. React in this case is the view.
'''


'''
TODO:
    - Create a method to check if the user does not have an active session and create one
''' 


class RoomView(generics.ListAPIView):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer


class GetRoom(APIView):
    serializer_class = RoomSerializer
    # specify that when we call this view we need to pass the code parameter of the room
    lookup_url_kwarg = 'code'

    def get(self, request, format=None):
        # getting the code from the info of the GET request
        code = request.GET.get(self.lookup_url_kwarg)
        if code is not None:
            room = Room.objects.filter(code=code)
            # room is unique so I should have at most one room
            if len(room) > 0:
                data = RoomSerializer(room[0]).data
                # create is_host as new key of the serializer
                # it contains if the session of the user is the key of the host of the room
                # so the view knows if the user that requested is the host
                print("jjfhajhfjahjfhajfhjafjajfha",self.request.session.session_key == room[0].host)
                data['is_host'] = self.request.session.session_key == room[0].host
                return Response(data, status=status.HTTP_200_OK)
            return Response({'Room Not Found': 'Invalid Room Code...'}, status=status.HTTP_400_BAD_REQUEST)
         
        return Response({'Bad Request': 'Room code not found in the request...'}, status=status.HTTP_400_BAD_REQUEST)


# Allow to join a new Room, by sending the room code
class JoinRoom(APIView):
    lookup_url_kwarg = 'code'

    def post(self, request, format=None):
        # check if the user does not have an active session and create one
        if not self.request.session.exists(self.request.session.session_key):
            self.request.session.create()

        code = request.data.get(self.lookup_url_kwarg)
        if code != None:
            room_result = Room.objects.filter(code=code)
            if len(room_result) > 0:
                room = room_result[0]
                # add into the sesssion the code in which room is the user.
                # So if later on they come back we can return them into the older room
                self.request.session['room_code'] = code
                return Response({'message': 'Room Joined Successfully!'}, status=status.HTTP_200_OK)

            return Response({'Bad Request': 'Invalid Room Code'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'Bad Request': 'Invalid data, did not find a room code key'}, status=status.HTTP_400_BAD_REQUEST)


class CreateRoomView(APIView):
    serializer_class = CreateRoomSerializer

    def post(self, request, format=None):
        # check if the user does not have an active session and create one
        if not self.request.session.exists(self.request.session.session_key):
            self.request.session.create()

        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            guest_can_pause = serializer.data.get('guest_can_pause')
            votes_to_skip = serializer.data.get('votes_to_skip')
            host = self.request.session.session_key
            queryset = Room.objects.filter(host=host)
            if queryset.exists():
                room = queryset[0]
                room.guest_can_pause = guest_can_pause
                room.votes_to_skip = votes_to_skip
                room.save(update_fields=['guest_can_pause', 'votes_to_skip'])
                # save code into session
                self.request.session['room_code'] = room.code
                return Response(RoomSerializer(room).data, status=status.HTTP_200_OK)
            else:
                room = Room(host=host, guest_can_pause=guest_can_pause,
                            votes_to_skip=votes_to_skip)
                room.save()
                # save code into session
                self.request.session['room_code'] = room.code
                return Response(RoomSerializer(room).data, status=status.HTTP_201_CREATED)

        return Response({'Bad Request': 'Invalid data...'}, status=status.HTTP_400_BAD_REQUEST)


# I want to check if a user is already in a room 
class UserInRoom(APIView):
    def get(self, request, format=None):
        # check if the user does not have an active session and create one
        if not self.request.session.exists(self.request.session.session_key):
            self.request.session.create()

        data = {
            'code': self.request.session.get('room_code')
        }
        return JsonResponse(data, status=status.HTTP_200_OK)

# When a user want to leave a room it is redirected to the home page.
# However the homepage redirect the user to the room because the user has the room code in its session.
# So we need to remove this code
# Also if the user is the host than we need to shut down the room
class LeaveRoom(APIView):
    def post(self, request, format=None):
        # if user has a room code in his session
        if 'room_code' in self.request.session:
            self.request.session.pop('room_code')
            # check if the user is the host
            host_id = self.request.session.session_key
            room_results = Room.objects.filter(host=host_id)
            # better queryset.exists()
            if len(room_results) > 0:
                room = room_results[0]
                room.delete()

        return Response({'Message': 'Successfully left room'}, status=status.HTTP_200_OK)


# Similar to create view but don't use it because in future:
#   - We may want to some user can have multiple rooms and we want to specify the room we want to update
#   - The host may want to make a user as an admin
class UpdateRoom(APIView):
    serializer_class = UpdateRoomSerializer
    # patch = update
    def patch(self, request, format=None):
        # check if the user does not have an active session and create one
        if not self.request.session.exists(self.request.session.session_key):
            self.request.session.create()
        
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            code = serializer.data.get('code')
            guest_can_pause = serializer.data.get('guest_can_pause')
            votes_to_skip = serializer.data.get('votes_to_skip')
            # search the room with the code passed in patch request
            queryset = Room.objects.filter(code=code)
            if not queryset.exists():
                return Response({'error': 'Room not found'}, status=status.HTTP_404_NOT_FOUND)
            
            room = queryset[0]
            # check if the user updating is the host of the room
            user_id = self.request.session_key
            if room.host != user_id:
                return Response({'error': 'You are not the host of the room'}, status=status.HTTP_403_FORBIDDEN)

            room.guest_can_pause = guest_can_pause
            room.votes_to_skip = votes_to_skip
            room.save(update_fields=['guest_can_pause', 'votes_to_skip'])
            return Response(RoomSerializer(room).data, status=status.HTTP_200_OK)


        return Response({'Bad Request': "Invalid Data"}, status=status.HTTP_400_BAD_REQUEST)