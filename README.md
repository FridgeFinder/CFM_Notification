# CFM_Notification

<p align="center">
  <a href="https://www.fridgefinder.app/">
    <img src="https://raw.githubusercontent.com/CollectiveFocus/CFM_Frontend/dev/public/feedback/happyFridge.svg" height="128">
  </a>
    <h1 align="center">FridgeFinder Notification Service</h1>
</p>

<p align="center">
  <a aria-label="GitHub Repo stars" href="https://github.com/FridgeFinder/CFM_Notification/">
    <img alt="" src="https://img.shields.io/github/stars/FridgeFinder/CFM_Notification?style=flat-square&labelColor=F6F6F6">
  </a>
  <img aria-label="GitHub contributors" alt="GitHub contributors" src="https://img.shields.io/github/contributors/FridgeFinder/CFM_Notification?style=flat-square&labelColor=F6F6F6">
  <img aria-label="GitHub commit activity (dev)" alt="GitHub commit activity (dev)" src="https://img.shields.io/github/commit-activity/m/FridgeFinder/CFM_Notification/main?style=flat-square&labelColor=F6F6F6">
  <a aria-label="Join the community on Discord" href="https://discord.com/channels/955884900655972463/955886184159125534">
    <img alt="" src="https://img.shields.io/badge/Join%20the%20community-yellow.svg?style=flat-square&logo=Discord&labelColor=F6F6F6">
  </a>
</p>

Service that manages and sends out User Fridge Notifications to users of FridgeFinder

User's of FridgeFinder are able to receive notification on status updates of a Community Fridge they are following

User's can Follow to a Community Fridge by going to a Fridge Profile and clicking on the Follow Button [TODO: implement follow button :)] - find one near you https://www.fridgefinder.app/browse

Currently User's can receive fridge notification via Email or SMS

---
## Pre-Requisites

1. AWS CLI - [Install the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
    * **You DO NOT have to create an AWS account to use AWS CLI for this project, skip these steps if you don't want to create an AWS account**
    * AWS CLI looks for credentials when using it, but doesn't validate. So will need to set some fake one. But the region name matters, use any valid region name. 
        ```sh
        $ aws configure
        $ AWS Access Key ID: [ANYTHING YOU WANT]
        $ AWS Secret Access Key: [ANYTHING YOUR HEART DESIRES]
        $ Default region nam: us-east-1
        $ Default output format [None]: (YOU CAN SKIP)
        ```
2. SAM CLI - [Install the SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
    * **You DO NOT need to create an aws account to use SAM CLI for this project, skip these steps if you don't want to create an aws account**
    * Note: if you are getting the following error: `runtime is not supported` when running `sam build --use-container` make sure your SAM CLI version is up to date
3. Python 3 - [Install Python 3](https://www.python.org/downloads/)
4. Docker - [Install Docker](https://docs.docker.com/get-docker/)

---

## Setup Local Database Connection

**Guide that was used:** https://betterprogramming.pub/how-to-deploy-a-local-serverless-application-with-aws-sam-b7b314c3048c

Follow these steps to get Dynamodb running locally

1. **Start a local DynamoDB service**
    ```sh
    $ docker compose up
    # OR if you want to run it in the background:
    $ docker compose up -d
    ```

2. **Create tables**
    ```sh
    $ ./scripts/create_local_dynamodb_tables.py
    ```

---
## Build and Test Locally

Confirm that the following requests work for you

1. `cd Notification/`
2. `sam build --use-container`
3. `sam local invoke HelloWorldFunction --event events/event.json`
    * response: ```{"statusCode": 200, "body": "{\"message\": \"hello world\"}"}```
4. `sam local start-api`
5. `curl http://localhost:3000/hello`
    * response: ```{"message": "hello world"}```

If it does yay, keep going 🤸‍♀️

---
### User Fridge Notification
These APIs are for interacting with individual user/fridge notification records

URL format: `v1/users/{user_id}/notifications/{fridge_id}`

Note: make sure your local dynamodb instance is running on docker. Follow instructions on `Setup Local Database Connection`

#### Local Invoke

To test locally we use `sam local invoke` to mimick a cognito authorized request

1. POST Example
    ```bash
    sam local invoke UserFridgeNotificationsFunction --event events/post_notification.json --parameter-overrides ParameterKey=Environment,ParameterValue=local ParameterKey=Stage,ParameterValue=dev --docker-network cfm-network
    ```

2. PUT Example
     ```bash
     sam local invoke UserFridgeNotificationsFunction --event events/put_notification.json --parameter-overrides ParameterKey=Environment,ParameterValue=local ParameterKey=Stage,ParameterValue=dev --docker-network cfm-network
     ```
     
3. GET Example
    ```bash
    sam local invoke UserFridgeNotificationsFunction --event events/get_notification.json --parameter-overrides ParameterKey=Environment,ParameterValue=local ParameterKey=Stage,ParameterValue=dev --docker-network cfm-network
    ```

---
## Running Unit Tests

1. Create and activate a virtual environment from the project root:

```sh
python3 -m venv .venv
source .venv/bin/activate
```

2. Upgrade packaging tools and install the project in editable mode:

```sh
pip install -U pip setuptools wheel
pip install -e .
```

3. Install test dependencies:

```sh
pip install -r Notification/tests/requirements.txt
```

4. Run tests (unittest discovery):

```sh
python -m unittest discover -s Notification/tests/unit -t .
```

Or run a single test file:

```sh
python -m unittest Notification.tests.unit.test_user_fridge_notifications_api
```

To deactivate the environment when done:
```sh
deactivate
```
