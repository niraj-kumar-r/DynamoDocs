import os
import tiktoken
import time
import traceback
from collections import defaultdict
from ollama import Client, ResponseError, RequestError, ChatResponse

from dynamodocs.mylogger import logger
from dynamodocs.prompt import SYSTEM_PROMPT, USER_PROMPT
from dynamodocs.tree_handler import DocItem
from dynamodocs.file_handler import FileHandler


class ContextLengthExceededError(Exception):
    """Exception raised when the input size exceeds the model's context length limit."""
    pass


def build_path_tree(who_reference_me, reference_who, doc_item_path):
    def tree():
        return defaultdict(tree)

    path_tree = tree()

    for path_list in [who_reference_me, reference_who]:
        for path in path_list:
            parts = path.split(os.sep)
            node = path_tree
            for part in parts:
                node = node[part]

    # handle doc_item_path
    parts = doc_item_path.split(os.sep)
    parts[-1] = "✳️" + parts[-1]
    # add a star before the last object
    node = path_tree
    for part in parts:
        node = node[part]

    def tree_to_string(tree, indent=0):
        s = ""
        for key, value in sorted(tree.items()):
            s += "    " * indent + key + "\n"
            if isinstance(value, dict):
                s += tree_to_string(value, indent + 1)
        return s

    return tree_to_string(path_tree)


class ChatEngine:
    """
    ChatEngine is used to generate the doc of functions or classes.
    """

    def __init__(self, CONFIG):
        self.config = CONFIG

    def num_tokens_from_string(self, string: str, encoding_name="cl100k_base") -> int:
        """Returns the number of tokens in a text string."""
        encoding = tiktoken.get_encoding(encoding_name)
        num_tokens = len(encoding.encode(string))
        return num_tokens

    def generate_doc(self, doc_item: DocItem, file_handler: FileHandler):
        code_info = doc_item.content
        referenced = len(doc_item.who_reference_me) > 0

        code_type = code_info["type"]
        code_name = code_info["name"]
        code_content = code_info["code_content"]
        have_return = code_info["have_return"]
        who_reference_me = doc_item.who_reference_me_name_list
        reference_who = doc_item.reference_who_name_list
        file_path = doc_item.get_full_name()
        doc_item_path = os.path.join(file_path, code_name)

        project_structure = build_path_tree(
            who_reference_me, reference_who, doc_item_path
        )

        def get_referenced_prompt(doc_item: DocItem) -> str:
            if len(doc_item.reference_who) == 0:
                return ""
            prompt = [
                """As you can see, the code calls the following objects, their code and docs are as following:"""
            ]
            for k, reference_item in enumerate(doc_item.reference_who):
                instance_prompt = (
                    f"""obj: {reference_item.get_full_name()}\nDocument: \n{reference_item.md_content[-1] if len(reference_item.md_content) > 0 else 'None'}\nRaw code:```\n{
                        reference_item.content['code_content'] if 'code_content' in reference_item.content.keys() else ''}\n```"""
                    + "=" * 10
                )
                prompt.append(instance_prompt)
            return "\n".join(prompt)

        def get_referencer_prompt(doc_item: DocItem) -> str:
            if len(doc_item.who_reference_me) == 0:
                return ""
            prompt = [
                """Also, the code has been called by the following objects, their code and docs are as following:"""
            ]
            for k, referencer_item in enumerate(doc_item.who_reference_me):
                instance_prompt = (
                    f"""obj: {referencer_item.get_full_name()}\nDocument: \n{referencer_item.md_content[-1] if len(referencer_item.md_content) > 0 else 'None'}\nRaw code:```\n{
                        referencer_item.content['code_content'] if 'code_content' in referencer_item.content.keys() else 'None'}\n```"""
                    + "=" * 10
                )
                prompt.append(instance_prompt)
            return "\n".join(prompt)

        def get_relationship_description(referencer_content, reference_letter):
            if referencer_content and reference_letter:
                has_relationship = "And please include the reference relationship with its callers and callees in the project from a functional perspective"
            elif referencer_content:
                return "And please include the relationship with its callers in the project from a functional perspective."
            elif reference_letter:
                return "And please include the relationship with its callees in the project from a functional perspective."
            else:
                return ""\

        max_tokens = self.config.get("max_document_tokens", 1024) or 1024
        max_attempts = 2  # Set the maximum number of attempts

        code_type_tell = "Class" if code_type == "ClassDef" else "Function"
        parameters_or_attribute = (
            "attributes" if code_type == "ClassDef" else "parameters"
        )
        have_return_tell = (
            "**Output Example**: Mock up a possible appearance of the code's return value."
            if have_return
            else ""
        )
        combine_ref_situation = (
            "and combine it with its calling situation in the project,"
            if referenced
            else ""
        )

        referencer_content = get_referencer_prompt(doc_item)
        reference_letter = get_referenced_prompt(doc_item)
        has_relationship = get_relationship_description(
            referencer_content, reference_letter)

        project_structure_prefix = ", and the related hierarchical structure of this project is as follows (The current object is marked with an *):"

        system_prompt = SYSTEM_PROMPT.format(
            combine_ref_situation=combine_ref_situation,
            file_path=file_path,
            project_structure_prefix=project_structure_prefix,
            project_structure=project_structure,
            code_type_tell=code_type_tell,
            code_name=code_name,
            code_content=code_content,
            have_return_tell=have_return_tell,
            has_relationship=has_relationship,
            reference_letter=reference_letter,
            referencer_content=referencer_content,
            parameters_or_attribute=parameters_or_attribute,
            language="English",
        )

        user_prompt = USER_PROMPT

        total_tokens = (
            self.num_tokens_from_string(system_prompt) +
            self.num_tokens_from_string(user_prompt)
        )

        if (total_tokens > max_tokens):
            logger.warning(
                f"Total tokens ({total_tokens}) exceed the maximum tokens ({max_tokens}).")
        else:
            logger.info(
                f"Total tokens ({total_tokens})."
            )

        try:
            client = Client(host=self.config["ollama_host"], timeout=30)
        # TODO : check if the connection is successful with the Ollama server
        # Make a check connection function for this as below would not work
        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            return {
                "content": f"{doc_item.get_full_name()} - [{doc_item.item_type}] : \ndocumentation to be generated"
            }

        attempt = 0
        while attempt < max_attempts:
            try:
                response: ChatResponse = client.chat(model=self.config["ollama_model"], messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                    stream=False,)

                if response.message is None:
                    attempt += 1
                    continue

                return response.message

            except RequestError as e:
                logger.warning(
                    f"Request error: {e}. Attempt {attempt + 1} of {max_attempts}")
                time.sleep(3)
                attempt += 1

            except ResponseError as e:
                logger.warning(
                    f"Response error: {e}. Attempt {attempt + 1} of {max_attempts}")
                time.sleep(3)
                attempt += 1

            except Exception as e:
                logger.warning(
                    f"An error occurred. Attempt {attempt + 1} of {max_attempts}")
                # logger.warning(traceback.format_exc())
                time.sleep(3)
                attempt += 1

        else:
            logger.error(
                f"Failed to generate documentation for {doc_item.get_full_name()}.")
            return {
                "content": f"{doc_item.get_full_name()} - [{doc_item.item_type}] : \ndocumentation to be generated"
            }
        # while attempt < max_attempts:

        #     try:
        #         # Get basic configuration
        #         client = OpenAI(
        #             # api_key=self.config["api_keys"][model][0]["api_key"],
        #             api_key="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",
        #             # base_url=self.config["api_keys"][model][0]["base_url"],
        #             base_url="https://api.openai.com/v1",
        #             # timeout=self.config["default_completion_kwargs"]["request_timeout"],
        #             timeout=60,
        #         )

            # messages = [
            #     {"role": "system", "content": system_prompt},
            #     {"role": "user", "content": user_prompt},
            # ]

        #         response = client.chat.completions.create(
        #             model=model,
        #             messages=messages,
        #             temperature=self.config["default_completion_kwargs"]["temperature"],
        #             max_tokens=max_tokens,
        #         )

        #         response_message = response.choices[0].message

        #         # If response_message is None, continue to the next loop
        #         if response_message is None:
        #             attempt += 1
        #             continue
        #         return response_message

        #     except APIConnectionError as e:
        #         logger.error(f"Connection error: {e}. Attempt {
        #                      attempt + 1} of {max_attempts}")
        #         # Retry after 7 seconds
        #         time.sleep(7)
        #         attempt += 1
        #         if attempt == max_attempts:
        #             raise
        #         else:
        #             continue  # Try to request again
        #     except Exception as e:
        #         logger.error(
        #             f"An unknown error occurred: {e}. \nAttempt {
        #                 attempt + 1} of {max_attempts}"
        #         )
        #         # Retry after 10 seconds
        #         time.sleep(10)
        #         attempt += 1
        #         if attempt == max_attempts:
        #             return None
