package webChat.userTest;

import java.util.ArrayList;
import java.util.List;

public class test {
    public static void main(String[] args){
        List<User> users = new ArrayList<User>();

        ChatUser chat = new ChatUser();
        chat.id = "new";
        chat.name = "test";

        users.add(chat);

        System.out.println("name : "+chat.name);

        ChatUser chat2 = (ChatUser) users.get(0);
        System.out.println("id : "+chat2.id);
    }
}
