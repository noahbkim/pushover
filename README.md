# Pushover

Despite there being numerous tutorials and sources of documentation online, it's still incredibly difficult to crack the code of Safari push notifications.
The documentation by Apple itself leaves much to be desired, and if you're not familiar with existing API's, such as that used to send all Apple push notifications, it can be impossible to crack the code.
Here's what I created to remedy this problem. 
Check out the full blog post <a href="https://noahbkim.com/code/2018/08/19/safari-notifications.html" target="_blank">here</a>.

## Using Pushover

Instead of having to deal with all of that (at least 8 hours of staring at examples, documentation, and error messages over the last two days), you can use my nifty `pushover.py` script.
To create a static push package, just run `pushover.py` with a complete `pushover.yml` configuration and it will spit out a `package.zip` in the build folder.
The reason I say static is because you might want to have a per-user notification management, but we'll get to that later.

For now, here's an example of the workflow.
First, install the Python environment, generate your icons, and run `pushover.py` to generate the empty config file:

```
$ pipenv install
$ pipenv shell
$ python icons.py original.png files/icon.iconset
$ python pushover.py
```

Fill out the config file with the location of your certificates, icon set, and website metadata.
My actual website configuration is in the `pushover` repository for reference.
Then run pushover again for real.

```
$ python pushover.py
```  

You'll find your `package.zip` in the `build/` directory.

## Setting up the Pushover Server

To fully setup website push notifications, you'll need more than just the push package.
You also need to fulfill a RESTful web API from the `webServiceURL` you provided in the website metadata.
This should respond to:

- `POST /v2/pushPackages/<push_id>` with the `package.zip`.
- `POST /v1/devices/<device_token>/registrations/<push_id>` with logic for user registration. Here you have to track the device ID of your new subscriber so you can send them notifications.
- `DELETE /v1/devices/<device_token>/registrations/<push_id>` for unregistering an users who have unsubscribed.
- `POST /v1/log` for error messages in JSON format.

I've implemented a minimal Flask <a href="https://github.com/noahbkim/pushover/blob/master/server.py" target="_blank">server</a> that does this in a script called `server.py` in the repository.
Set it up with an SSL certificate and some sort of reverse proxy on your `webServiceURL` so that it can respond to HTTPS requests, and you're good to go.
I used `push.noahbkim.com` so I wouldn't have to mess with my simple Jekyll Nginx configuration.

## Sending Push Notifications

The final part of the equation is sending the actual push notifications.
Apparently everyone should know how to do this, as Apple's explanation is basically just "do it" with the following payload format.
I also spent a significant amount of trying to decode this system, and came up with the <a href="https://github.com/noahbkim/pushover/blob/master/notify.py" target="_blank">notify</a> script.
There are actually several other programs that allow you to send push notifications, but if you want to know how it works, check out the code in the repository.

