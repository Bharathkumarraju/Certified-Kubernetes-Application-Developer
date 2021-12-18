import json
import boto3
import time

organizations = boto3.client('organizations')
ses = boto3.client('ses')
sns_client = boto3.client('sns')

sns_topic_arn = "arn:aws:sns:us-east-1:172586632398:aws_account_status"

from_email = " bhrth.dsra1@gmail.com"
email_subject = "Welcome to AWS managed by Singtel"
email_body = """Hi Team,
	
Thanks for Joining with Singtel.

Please login with your email to login as root user to AWS Console https://console.aws.amazon.com/
And for the first time click on the link "Forgot your password" to reset your password.

As a best practise please create your own IAM users,roles and policies etc.


Regards,
The Singtel Cloud Team."""
def send_email(source_email, destination_email, mail_subject, mail_body):
    try:
        response = ses.send_email(
    	    Source = source_email,
    	    Destination = {
    		    'ToAddresses': [
    			    destination_email
    		    ]
    	    },
    	    Message = {
    		    'Subject': {
    			    'Data': mail_subject,
    			    'Charset': 'UTF-8'
    		    },
    		    'Body': {
    			    'Text':{
    				    'Data': mail_body,
    				    'Charset': 'UTF-8'
    			    }
    		    }
    	    }
        )
    
        print('Successfully sent email from Lambda using Amazon SES')
        return response
    except Exception as e:
        print(e)
        raise e


def create_organizational_unit(ou_name, parent_id, tags):
    try:
        response = organizations.create_organizational_unit(
            ParentId=parent_id,
            Name=ou_name,
            Tags=tags
        )
        print("Organizational unit {} created successfuly!".format(ou_name))
        return response
    except Exception as e:
        print("Error creating organizational unit {}".format(ou_name))
        print(e)
        raise e
    

def create_account(email, account_name, role_name, access_to_billing, tags):
    try:
        createAccount = organizations.create_account(
            Email=email,
            AccountName=account_name,
            RoleName=role_name,
            IamUserAccessToBilling=access_to_billing,
            Tags=tags
        )
        print("Account {} created successfully!".format(account_name))
        return createAccount
    except Exception as e:
        print("Error creating account {}".format(account_name))
        print(e)
        raise e

def move_account_to_ou(account_id, source_parent_id, destination_parent_id):
    try:
        moveAccount = organizations.move_account(
            AccountId=account_id,
            SourceParentId=source_parent_id,
            DestinationParentId=destination_parent_id
        )
        print("Account moved to OU successfuly!")
        return moveAccount
    except Exception as e:
        print("Error moving account to provided OU.")
        print(e)
        raise e
        
# Send message to SNS topic
def send_msg_to_sns(topic_arn, subject, message):
    response = sns_client.publish(
        TargetArn=topic_arn,
        Message=json.dumps({'default': json.dumps(message, indent=4, sort_keys=True)}),
        Subject= subject,
        MessageStructure='json'
    )

def lambda_handler(event, context):
    sns_message = event['Records'][0]['Sns']['Message']
    message = json.loads(sns_message)
    
    email = message['email']
    account_name = message['account_name']
    role_name = message['role_name']
    access_to_billing = message['access_to_billing']
    root_id = message['root_id']
    ou_name = message['ou_name']
    ou_parent_id = message['ou_parent_id']
    ou_tags = message['ou_tags']
    account_tags = message['account_tags']
    
    # CreateOU and send the destination for new account to this OU
    createOU = create_organizational_unit(ou_name, ou_parent_id, ou_tags)
    
    source_parent_id = root_id
    destination_parent_id = createOU['OrganizationalUnit']['Id']
    
    
    createAccount = create_account(email, account_name, role_name, access_to_billing, account_tags)
    create_account_request_id = createAccount['CreateAccountStatus']['Id']
        
    state = organizations.describe_create_account_status(
        CreateAccountRequestId=create_account_request_id
    )['CreateAccountStatus']['State']

    while state == 'IN_PROGRESS':
        print("Waiting for 2 seconds...")
        time.sleep(2)
        state = organizations.describe_create_account_status(
            CreateAccountRequestId=create_account_request_id
        )['CreateAccountStatus']['State']
        print("Account creation state is: {}".format(state))

    
    if state == 'SUCCEEDED':
        account_id = organizations.describe_create_account_status(
            CreateAccountRequestId=create_account_request_id
        )['CreateAccountStatus']['AccountId']
        
        moveAccount = move_account_to_ou(account_id, source_parent_id, destination_parent_id)
        
        # send email
        source_email = from_email
        destination_email = email
        mail_subject = email_subject
        mail_body = email_body
        response = send_email(source_email, destination_email, mail_subject, mail_body)
        
        sns_email_subject = "Status of new AWS account for: " +  email
        sns_body = {"message": "AWS account created successfully with account id: " + str(account_id)}
        send_msg_to_sns(sns_topic_arn, sns_email_subject, sns_body)
    elif state == 'FAILED':
        failure_reason = organizations.describe_create_account_status(
            CreateAccountRequestId=create_account_request_id
        )['CreateAccountStatus']['FailureReason']
        print("Account creation failed!!")
        print('FailureReason: {}'.format(failure_reason))
        sns_email_subject = "Status of new AWS account for: " +  email
        sns_body = {"message": "Failed to create AWS account", "reason": failure_reason}
        send_msg_to_sns(sns_topic_arn, sns_email_subject, sns_body)
    