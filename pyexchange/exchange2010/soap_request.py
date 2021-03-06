"""
(c) 2013 LinkedIn Corp. All rights reserved.
Licensed under the Apache License, Version 2.0 (the "License");?you may not use this file except in compliance with the License. You may obtain a copy of the License at  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software?distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
"""
from lxml.builder import ElementMaker
from ..utils import convert_datetime_to_utc

MSG_NS = u'http://schemas.microsoft.com/exchange/services/2006/messages'
TYPE_NS = u'http://schemas.microsoft.com/exchange/services/2006/types'
SOAP_NS = u'http://schemas.xmlsoap.org/soap/envelope/'

NAMESPACES = {u'm': MSG_NS, u't': TYPE_NS, u's': SOAP_NS}

M = ElementMaker(namespace=MSG_NS, nsmap=NAMESPACES)
T = ElementMaker(namespace=TYPE_NS, nsmap=NAMESPACES)

EXCHANGE_DATE_FORMAT = u"%Y-%m-%dT%H:%M:%SZ"


def resource_node(element, resources):
  """
  Helper function to generate a person/conference room node from an email address

  <t:OptionalAttendees>
    <t:Attendee>
        <t:Mailbox>
            <t:EmailAddress>{{ attendee_email }}</t:EmailAddress>
        </t:Mailbox>
    </t:Attendee>
  </t:OptionalAttendees>
  """

  for attendee in resources:
    element.append(
      T.Attendee(
        T.Mailbox(
          T.EmailAddress(attendee.email)
        )
      )
    )

  return element


def delete_field(field_uri):
  """
      Helper function to request deletion of a field. This is necessary when you want to overwrite values instead of
      appending.

      <t:DeleteItemField>
        <t:FieldURI FieldURI="calendar:Resources"/>
      </t:DeleteItemField>
  """

  root = T.DeleteItemField(
    T.FieldURI(FieldURI=field_uri)
  )

  return root


def get_item(exchange_id, format=u"Default"):
  """
    Requests a calendar item from the store.

    exchange_id is the id for this event in the Exchange store.

    format controls how much data you get back from Exchange. Full docs are here, but acceptible values
    are IdOnly, Default, and AllProperties.

    http://msdn.microsoft.com/en-us/library/aa564509(v=exchg.140).aspx

    <m:GetItem  xmlns:m="http://schemas.microsoft.com/exchange/services/2006/messages"
            xmlns:t="http://schemas.microsoft.com/exchange/services/2006/types">
      <m:ItemShape>
          <t:BaseShape>{format}</t:BaseShape>
      </m:ItemShape>
      <m:ItemIds>
          <t:ItemId Id="{exchange_id}"/>
      </m:ItemIds>
  </m:GetItem>

  """

  root = M.GetItem(
    M.ItemShape(
      T.BaseShape(format)
    ),
    M.ItemIds(
      T.ItemId(Id=exchange_id)
    )
  )
  return root


def new_event(event):
  """
  Requests a new event be created in the store.

  http://msdn.microsoft.com/en-us/library/aa564690(v=exchg.140).aspx

  <m:CreateItem SendMeetingInvitations="SendToAllAndSaveCopy"
              xmlns:m="http://schemas.microsoft.com/exchange/services/2006/messages"
              xmlns:t="http://schemas.microsoft.com/exchange/services/2006/types">
    <m:SavedItemFolderId>
        <t:DistinguishedFolderId Id="calendar"/>
    </m:SavedItemFolderId>
    <m:Items>
        <t:CalendarItem>
            <t:Subject>{event.subject}</t:Subject>
            <t:Body BodyType="HTML">{event.subject}</t:Body>
            <t:Start></t:Start>
            <t:End></t:End>
            <t:Location></t:Location>
            <t:RequiredAttendees>
                {% for attendee_email in meeting.required_attendees %}
                <t:Attendee>
                    <t:Mailbox>
                        <t:EmailAddress>{{ attendee_email }}</t:EmailAddress>
                    </t:Mailbox>
                </t:Attendee>
             HTTPretty   {% endfor %}
            </t:RequiredAttendees>
            {% if meeting.optional_attendees %}
            <t:OptionalAttendees>
                {% for attendee_email in meeting.optional_attendees %}
                    <t:Attendee>
                        <t:Mailbox>
                            <t:EmailAddress>{{ attendee_email }}</t:EmailAddress>
                        </t:Mailbox>
                    </t:Attendee>
                {% endfor %}
            </t:OptionalAttendees>
            {% endif %}
            {% if meeting.conference_room %}
            <t:Resources>
                <t:Attendee>
                    <t:Mailbox>
                        <t:EmailAddress>{{ meeting.conference_room.email }}</t:EmailAddress>
                    </t:Mailbox>
                </t:Attendee>
            </t:Resources>
            {% endif %}
            </t:CalendarItem>
    </m:Items>
</m:CreateItem>
  """

  start = convert_datetime_to_utc(event.start)
  end = convert_datetime_to_utc(event.end)

  root = M.CreateItem(
    M.SavedItemFolderId(
      T.DistinguishedFolderId(Id="calendar")
    ),
    M.Items(
      T.CalendarItem(
        T.Subject(event.subject),
        T.Body(event.body or u'', BodyType="HTML"),
        T.Start(start.strftime(EXCHANGE_DATE_FORMAT)),
        T.End(end.strftime(EXCHANGE_DATE_FORMAT)),
        T.Location(event.location or u''),
      )
    ),
    SendMeetingInvitations="SendToAllAndSaveCopy"
  )

  calendar_node = root.xpath(u'/m:CreateItem/m:Items/t:CalendarItem', namespaces=NAMESPACES)[0]

  if event.required_attendees:
    calendar_node.append(resource_node(element=T.RequiredAttendees(), resources=event.required_attendees))

  if event.optional_attendees:
    calendar_node.append(resource_node(element=T.OptionalAttendees(), resources=event.optional_attendees))

  if event.resources:
    calendar_node.append(resource_node(element=T.Resources(), resources=event.resources))

  return root


def delete_event(event):
    """

    Requests an item be deleted from the store.


    <DeleteItem
        xmlns="http://schemas.microsoft.com/exchange/services/2006/messages"
        xmlns:t="http://schemas.microsoft.com/exchange/services/2006/types"
        DeleteType="HardDelete"
        SendMeetingCancellations="SendToAllAndSaveCopy"
        AffectedTaskOccurrences="AllOccurrences">
            <ItemIds>
                <t:ItemId Id="{{ id }}" ChangeKey="{{ change_key }}"/>
            </ItemIds>
    </DeleteItem>

    """
    root = M.DeleteItem(
            M.ItemIds(
              T.ItemId(Id=event.id, ChangeKey=event.change_key)
            ),
          DeleteType="HardDelete",
          SendMeetingCancellations="SendToAllAndSaveCopy",
          AffectedTaskOccurrences="AllOccurrences"
    )

    return root


def update_property_node(node_to_insert, field_uri):
  """ Helper function - generates a SetItemField which tells Exchange you want to overwrite the contents of a field."""
  root = T.SetItemField(
            T.FieldURI(FieldURI=field_uri),
            T.CalendarItem(node_to_insert)
        )
  return root


def update_item(event, updated_attributes, send_only_to_changed_attendees=False):
  """ Saves updates to an event in the store. Only request changes for attributes that have actually changed."""

  SEND_MEETING_INVITES = u"SendToChangedAndSaveCopy" if send_only_to_changed_attendees else u"SendToAllAndSaveCopy"

  root = M.UpdateItem(
            M.ItemChanges(
              T.ItemChange(
                T.ItemId(Id=event.id, ChangeKey=event.change_key),
                T.Updates()
              )

            ),
          ConflictResolution=u"AlwaysOverwrite",
          MessageDisposition=u"SendAndSaveCopy",
          SendMeetingInvitationsOrCancellations=SEND_MEETING_INVITES
    )

  update_node = root.xpath(u'/m:UpdateItem/m:ItemChanges/t:ItemChange/t:Updates', namespaces=NAMESPACES)[0]

  if not send_only_to_changed_attendees:
    # We want to resend invites, which you do by setting an attribute to the same value it has. Right now, events
    # are always scheduled as Busy time, so we just set that again.
    update_node.append(
      update_property_node(field_uri="calendar:LegacyFreeBusyStatus", node_to_insert=T.LegacyFreeBusyStatus("Busy"))
    )

  if u'html_body' in updated_attributes:
    update_node.append(
      update_property_node(field_uri="item:Body", node_to_insert=T.Body(event.html_body, BodyType="HTML"))
    )

  if u'text_body' in updated_attributes:
    update_node.append(
      update_property_node(field_uri="item:Body", node_to_insert=T.Body(event.text_body, BodyType="Text"))
    )

  if u'subject' in updated_attributes:
    update_node.append(
      update_property_node(field_uri="item:Subject", node_to_insert=T.Subject(event.subject))
    )

  if u'start' in updated_attributes:
    start = convert_datetime_to_utc(event.start)

    update_node.append(
      update_property_node(field_uri="calendar:Start", node_to_insert=T.Start(start.strftime(EXCHANGE_DATE_FORMAT)))
    )

  if u'end' in updated_attributes:
    end = convert_datetime_to_utc(event.end)

    update_node.append(
      update_property_node(field_uri="calendar:End", node_to_insert=T.End(end.strftime(EXCHANGE_DATE_FORMAT)))
    )

  if u'location' in updated_attributes:
    update_node.append(
      update_property_node(field_uri="calendar:Location", node_to_insert=T.Location(event.location))
    )

  if u'attendees' in updated_attributes:

    if event.required_attendees:
      required = resource_node(element=T.RequiredAttendees(), resources=event.required_attendees)

      update_node.append(
        update_property_node(field_uri="calendar:RequiredAttendees", node_to_insert=required)
      )
    else:
      update_node.append(delete_field(field_uri="calendar:RequiredAttendees"))

    if event.optional_attendees:
      optional = resource_node(element=T.OptionalAttendees(), resources=event.optional_attendees)

      update_node.append(
        update_property_node(field_uri="calendar:OptionalAttendees", node_to_insert=optional)
      )
    else:
      update_node.append(delete_field(field_uri="calendar:OptionalAttendees"))

  if u'resources' in updated_attributes:
    if event.resources:
      resources = resource_node(element=T.Resources(), resources=event.resources)

      update_node.append(
        update_property_node(field_uri="calendar:Resources", node_to_insert=resources)
      )
    else:
      update_node.append(delete_field(field_uri="calendar:Resources"))

  return root
