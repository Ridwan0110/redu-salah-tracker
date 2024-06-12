from tkcalendar import Calendar
import datetime


class CustomCalendar(Calendar):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tag_config('all_done', background='green')
        self.tag_config('some_done', background='yellow')

    def update_date_colors(self, date_status):
        """
        Update the colors of calendar dates based on completion status.

        Parameters:
            date_status (dict): A dictionary containing dates as keys and completion statuses ('all_done' or 'some_done') as values.
        """
        # Clear all tags
        for date in self._tags.keys():
            self.calevent_remove(date, 'all_done')
            self.calevent_remove(date, 'some_done')

        # Apply new tags based on status
        for date, status in date_status.items():
            # Convert date string to datetime.date object
            date_obj = datetime.datetime.strptime(date, '%m/%d/%y').date()

            if status == 'all_done':
                self.calevent_create(date_obj, '', tags='all_done')
            elif status == 'some_done':
                self.calevent_create(date_obj, '', tags='some_done')
