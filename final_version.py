import numpy as np
import sqlite3
import re
import datetime
import xml.etree.ElementTree as ET
import match


def get_db(path):
    db_user = sqlite3.connect(path)
    db_user.row_factory = lambda cursor, row: row[0]
    cursor_db_user = db_user.cursor()

    return db_user, cursor_db_user


def get_internal_message_ids(db_user, cursor_db_user):
    message_ids = db_user.execute("SELECT DISTINCT filedMessageID FROM filedMessageContacts").fetchall()
    message_id_to_contacts = {}

    for message_id in message_ids:
        contacts_list = cursor_db_user.execute("SELECT contactId FROM filedMessageContacts WHERE filedMessageId=?",
                                               ([message_id])).fetchall()
        message_id_to_contacts[message_id] = contacts_list

    internal_message_ids = []

    for message_id, contact_ids in message_id_to_contacts.items():
        flag = True
        contact_type = []

        for contact_id in contact_ids:
            contact_type.append(
                db_user.execute("SELECT isInternal FROM contacts WHERE id=?", ([contact_id])).fetchall())

        for c_type in contact_type:
            if c_type[0] == 0:
                flag = False
                break
        if flag:
            internal_message_ids.append(message_id)

    return internal_message_ids


def get_subjects_matters(internal_message_ids, db_user):
    subjects = []
    matters = []

    for message_id in internal_message_ids:
        subjects.append(db_user.execute("SELECT subject FROM filedMessages WHERE id=?", ([message_id])).fetchall())
        matters.append(
            db_user.execute("SELECT DisplayValue FROM filedMessageAttributes WHERE Name='Matter' AND filedMessageId=?",
                            ([message_id])).fetchall())

    return subjects, matters


def get_matter_display_value(matter_id, db_user):
    return db_user.execute("SELECT description FROM attributes WHERE id=?", ([matter_id])).fetchall()


def get_statistics(xml_root):
    no_predictions = 0
    wrong_predictions_dates = []
    auto_file_predictions = 0  # have only 1 prediction
    no_prediction_dates= []
    number_of_right_predictions = 0
    manual_filing_dates = []

    prediction_xml = xml_root.findall("Prediction")

    for prediction in prediction_xml:

        predicted_values = prediction.findall("PredictedValues")
        original_values = prediction.findall("OriginalFiledValues")

        if predicted_values:

            if len(predicted_values) == 1:

                pred_value_1 = predicted_values[0].find(".//PredictedValue[@Key='1']").get("Value")
                pred_value_2 = predicted_values[0].find(".//PredictedValue[@Key='2']").get("Value")

                if original_values[0].find(".//OriginalFiledValue[@Key='1']").get("Value") == pred_value_1 and original_values[0].find(".//OriginalFiledValue[@Key='2']").get("Value") == pred_value_2:
                    number_of_right_predictions += 1
                    auto_file_predictions += 1
                else:
                    wrong_predictions_dates.append(prediction.find("PredictionDate").text)

            else:
                check = False
                for item in predicted_values:
                    pred_val_1 = item.find(".//PredictedValue[@Key='1']").get("Value")
                    pred_val_2 = item.find(".//PredictedValue[@Key='2']").get("Value")

                    if original_values[0].find(".//OriginalFiledValue[@Key='1']").get("Value") == pred_val_1 and original_values[0].find(".//OriginalFiledValue[@Key='2']").get("Value") == pred_val_2:
                        number_of_right_predictions += 1
                        manual_filing_dates.append(prediction.find("PredictionDate").text)
                        check = False
                        break

                    else:
                        check = True
                if check:
                    wrong_predictions_dates.append(prediction.find("PredictionDate").text)

        else:
            no_predictions += 1
            no_prediction_dates.append(prediction.find("PredictionDate").text)

    return no_predictions, auto_file_predictions, number_of_right_predictions, wrong_predictions_dates, no_prediction_dates, manual_filing_dates


def get_no_pred_subjects(user_sent_dates, db_user):
    id_subject = []
    just_subjects = []
    for sent_date in user_sent_dates:
        temp_date = "'" + (
            datetime.datetime.strptime(sent_date, '%m/%d/%Y %I:%M:%S %p').strftime('%Y-%m-%d %H:%M:%S')).replace(" ",
                                                                                                                 "T") + "%'"
        subject = db_user.execute(
            'SELECT subject FROM filedMessages WHERE sentDate LIKE {}'.format(temp_date)).fetchall()
        message_id = db_user.execute('SELECT id FROM filedMessages WHERE sentDate LIKE {}'.format(temp_date)).fetchall()
        id_subject.append((message_id, subject))
        just_subjects.append(subject)

    return just_subjects, id_subject


def get_subject_by_date(user_sent_date, db_user):
    temp_date = "'" + (
        datetime.datetime.strptime(user_sent_date, '%m/%d/%Y %I:%M:%S %p').strftime('%Y-%m-%d %H:%M:%S')).replace(" ",
                                                                                                                  "T") + "%'"
    subject = db_user.execute('SELECT subject FROM filedMessages WHERE sentDate LIKE {}'.format(temp_date)).fetchall()

    return subject


def get_matter_by_date(user_sent_date, db_user):
    temporary_date = "'" + (
        datetime.datetime.strptime(user_sent_date, '%m/%d/%Y %I:%M:%S %p').strftime('%Y-%m-%d %H:%M:%S')).replace(" ",
                                                                                                                  "T") + "%'"
    mess_id = db_user.execute('SELECT id FROM filedMessages WHERE sentDate LIKE {}'.format(temporary_date)).fetchall()

    return db_user.execute("SELECT DisplayValue FROM filedMessageAttributes WHERE Name='Matter' AND filedMessageId=?",
                           ([mess_id[0]])).fetchall()


def get_no_pred_matters(user_id_subject, db_user):
    id_matters = []

    for mes_id in user_id_subject:
        for m_id in mes_id[0]:
            id_matter = db_user.execute(
                'SELECT displayValue FROM filedMessageAttributes WHERE Name="Matter" AND filedMessageId=?',
                ([m_id])).fetchall()
            id_matters.append(id_matter)

    return id_matters


def more_than_one_prediction(xml_tree_user, db_user):
    prediction_nodes = xml_tree_user.findall("Prediction")
    real_matters = []
    all_subjects = []
    matters_to_choose = []

    for pred_node in prediction_nodes:

        matters_descriptions = []
        pred_date = pred_node.find("PredictionDate").text
        pred_values = pred_node.findall("PredictedValues")

        if len(pred_values) > 1:

            #     get matters list of the prediction node
            for pred_value in pred_values:
                matter_key = pred_value.find(".//PredictedValue[@Key='2']").get("Value")
                matter_description = get_matter_display_value(matter_key, db_user)
                matters_descriptions.append(matter_description)

            matters_to_choose.append(matters_descriptions)

            #  get subject of the prediciton node
            sub = get_subject_by_date(pred_date, db_user)
            all_subjects.append(sub)

            # get real matter of the prediction node
            real_matter = get_matter_by_date(pred_date, db_user)
            real_matters.append([real_matter[0].split("- ")[1]])

    return all_subjects, real_matters, matters_to_choose


def write_output(db_path_user, xml_path_user):

    # get database
    db_user, cursor_db_user= get_db(db_path_user)
    int_ids_user = get_internal_message_ids(db_user, cursor_db_user)

    subjects_user, matters_user = get_subjects_matters(int_ids_user, db_user)
    uni_matters_user = np.unique(matters_user)

    print("only internal")
    print(match.get_numbers(subjects_user, matters_user, uni_matters_user))

    # get xml
    tree_user = ET.ElementTree(file=xml_path_user)
    root_user = tree_user.getroot()

    user_stat = get_statistics(root_user)
    user_sent_dates = user_stat[4]
    user_manual_filing_dates = user_stat[5]

    user_no_pred_subjects, user_id_subject = get_no_pred_subjects(user_sent_dates, db_user)
    user_no_pred_matters = get_no_pred_matters(user_id_subject, db_user)

    print("----all statistics----")
    print(get_statistics(root_user))

    print("----no prediction----")
    print(match.get_numbers(user_no_pred_subjects, user_no_pred_matters, uni_matters_user))

    all_subjects_user, real_matters_user, matters_to_choose_user = more_than_one_prediction(tree_user,
                                                                                            db_user)
    print("----more than 1 prediction----")
    print(match.get_numbers_for_manual_filing_preds(all_subjects_user, real_matters_user, matters_to_choose_user))


if __name__ == "__main__":


    db_path_alexandria = '/Users/sparikdzya/Downloads/Predictions Log 8-7-18/Alexandria Carraher Predictions Log 8-7-18/db/NG-V540IA9C.db'

    xml_path_alexandria = '/Users/sparikdzya/Downloads/Predictions Log 8-7-18/Alexandria Carraher Predictions Log 8-7-18/PredictionLog2018871757.xml'

    write_output(db_path_alexandria, xml_path_alexandria)
